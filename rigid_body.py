from importlib.metadata import SelectableGroups
import moderngl as mgl
from moderngl_window import resources
from moderngl_window.scene import Scene
from moderngl_window.meta import SceneDescription, ProgramDescription
from moderngl_window.geometry.attributes import AttributeNames
from moderngl_window.opengl.vao import VAO
from moderngl_window.geometry import quad_fs, quad_2d
from pyrr import Matrix33 as m33
from pyrr import Matrix44 as m44
import numpy as np

def load_scene(
    path: str, cache=False, attr_names=AttributeNames, kind=None, **kwargs
) -> Scene:
    """Loads a scene"""

    return resources.scenes.load(
        SceneDescription(
            path=path, cache=cache, attr_names=attr_names, kind=kind, **kwargs,
        )
    )

def load_program(path=None) -> mgl.Program:
    return resources.programs.load(
        ProgramDescription(
            path=path,
        )
    )

class RigidBody():

    def __init__(self, rho=1.):

        self.pos = np.zeros(3, dtype='f4')
        self.ang = np.zeros(3, dtype='f4')
        
        self.lin_vel = np.zeros(3, dtype='f4')
        self.lin_acc = np.zeros(3, dtype='f4')

        self.ang_vel = np.zeros(3, dtype='f4')
        self.ang_acc = np.zeros(3, dtype='f4')

        self.rot_mat: m44 = self.gen_rot_mat44()
        self.trans_mat: m44 = self.gen_trans_matrix()

        self.next_lin_acc = np.zeros(3, dtype='f4')
        self.next_ang_acc = np.zeros(3, dtype='f4')
    
        # mass props
        self.inertia_world = m33.identity('f4')
        R = self.gen_rot_mat33()
        self.inertia_local = np.abs(R@self.inertia_world@R.T)
        self.rho = rho
        self.vol = 1
        self.mass = self.vol*self.rho

        # print(self.inertia_world, self.inertia_local)

    def _cross(self, a, b):
        c = [a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0]]
        return np.array(c, dtype='f4')

    def apply_force(self, F, app_pt=np.zeros(3, dtype='f4')):
        ''' Apply force to the object

            If Force is applied on a point different from the Center of Mass,
            also the resulting Torque is integrated, generating a rotation
        '''
        self.next_lin_acc += np.array(F, dtype='f4')/self.mass

        r = self.pos-app_pt # arm of the force
        torque = -self._cross(r, F)
        self.next_ang_acc += np.array(np.linalg.inv(self.inertia_local) @ torque)

        # print(self.next_ang_acc, self.next_lin_acc)
    
    def integrate(self, dt):
        ''' Integrate motion after applying all forces using Verlet algorithm
            # HELP: https://physics.stackexchange.com/questions/688426/compute-angular-acceleration-from-torque-in-3d
        '''

        # Angular Motion
        self.ang = self.ang + self.ang_vel*dt + self.ang_acc*(dt*dt*0.5)
        self.ang_vel = self.ang_vel + (self.ang_acc+self.next_ang_acc)*(dt*0.5)
        self.ang_acc = self.next_ang_acc
        
        # Linear Motion
        self.pos = self.pos + self.lin_vel*dt + self.lin_acc*(dt*dt*0.5)
        self.lin_vel = self.lin_vel + (self.lin_acc+self.next_lin_acc)*(dt*0.5)
        self.lin_acc = self.next_lin_acc

        # reset forces
        self.next_ang_acc = np.zeros(3, dtype='f4')
        self.next_lin_acc = np.zeros(3, dtype='f4')

        self.rot_mat = self.gen_rot_mat44()
        self.trans_mat = self.gen_trans_matrix()
        

    def gen_rot_mat33(self):
        xrot, yrot, zrot = self.ang
        return (m33.from_x_rotation(xrot)*m33.from_y_rotation(yrot)*m33.from_z_rotation(zrot)).astype('f4')

    def gen_rot_mat44(self):
        xrot, yrot, zrot = self.ang
        return (m44.from_x_rotation(xrot)*m44.from_y_rotation(yrot)*m44.from_z_rotation(zrot)).astype('f4')

    def gen_trans_matrix(self):
        return m44.from_translation(self.pos, dtype='f4')

    def gen_model_matrix(self):
        return (self.trans_mat*self.rot_mat).astype('f4')



class BouyantRigidBody(RigidBody):

    def __init__(self, ctx:mgl.Context,  obj:str, rho=1.):
        super().__init__(rho=1.)

        self.ctx = ctx
        self.scene: Scene = load_scene(obj)
        self.vao: VAO = self.scene.meshes[0].vao

        self.surf_prog: mgl.Program= None
        self.surf_vao: VAO = None
        self.surf_tex: mgl.Texture = None
        self.surf_norm: mgl.Texture = None
        self.surf_ws = None # wavescale
        self.surf_ch = None # choppyness
        self.surf_size = None

        # ---------------

        self.x_bound = [-1.5, 1.5]
        self.y_bound = [-1.5, 1.5]
        self.orto_proj:m44 = m44.orthogonal_projection(*self.x_bound, *self.y_bound, -5, 5)
        
        self.N = 128
        self.log2N = int(np.log2(self.N))
        
        self.dx = np.abs(self.x_bound[0]-self.x_bound[1])/self.N
        self.dy = np.abs(self.y_bound[0]-self.y_bound[1])/self.N

        self.n_layer = 4

        # ---------------------- OFF SCREEN FRAMEBUFFER
        self.depth_tex = self.ctx.depth_texture((self.N*self.n_layer, self.N))
        self.peel_tex = self.ctx.texture((self.N*self.n_layer, self.N), components=4, dtype='f4')

        self.mass_tex0 = self.ctx.texture((self.N*self.n_layer, self.N), components=4, dtype='f4')
        self.mass_tex1 = self.ctx.texture((self.N*self.n_layer, self.N), components=4, dtype='f4')
        self.mass_tex2 = self.ctx.texture((self.N*self.n_layer, self.N), components=4, dtype='f4')
        
        self.fb = self.ctx.framebuffer([self.peel_tex, self.mass_tex0, self.mass_tex1, self.mass_tex2], self.depth_tex)
        self.viewport = self.fb.viewport
        self.scissor = self.fb.scissor

        self.peel_prog = load_program("shader/peel.glsl")
        
        #---------------------- COPY FRAMEBUFFER
        self.copy_tex = self.ctx.texture((self.N*self.n_layer, self.N), components=4, dtype='f4')
        self.copy_tex.filter = mgl.NEAREST, mgl.NEAREST
        self.copy_fb = self.ctx.framebuffer(color_attachments=(self.copy_tex))

        self.ctx.enable(mgl.DEPTH_TEST)
        self.ctx.disable(mgl.CULL_FACE)

        # ---------
        self.quad = quad_fs()
        self.plane = quad_2d((5, 5))

        self.calc_mass_prop()

    def calc_mass_prop(self, full=False):

        view_mat: m44 = self.gen_look_at(
            self.pos+np.array([0, 0, 1]),
            self.pos,
            np.array([0, -1, 0]))

        self.peel_prog['proj'].write(self.orto_proj.astype('f4'))
        self.peel_prog['view'].write(view_mat.astype('f4'))
        self.peel_prog['model'].write(self.gen_model_matrix().astype('f4'))

        self.fb.clear()
        self.fb.use()
        self.fb.viewport = 0, 0, self.N, self.N
        self.vao.render(self.peel_prog)
        
    def load_surface(self, surf_prog, surf_vao, surf_tex, surf_norm, choppy, wavescale, surf_size):
        self.surf_prog = surf_prog
        self.surf_vao = surf_vao
        self.surf_tex = surf_tex
        self.surf_norm = surf_norm
        self.surf_ws = wavescale # wavescale
        self.surf_ch = choppy
        self.surf_size = surf_size
    
    def render_surf(self, proj: m44, view: m44):
        self.ctx.enable(mgl.DEPTH_TEST)
        self.surf_prog['proj'].write(proj.astype('f4'))
        self.surf_prog['view'].write(view.astype('f4'))
        self.surf_prog['model'].write(m44.identity().astype('f4'))
        self.surf_prog['scale_model'].write(m44.from_scale([self.surf_size/2]*3).astype('f4'))
        self.surf_prog['choppy'].value = self.surf_ch
        self.surf_prog['wave_scale'].value = self.surf_ws
        
        self.surf_tex.use(0)
        self.surf_norm.use(1)
        self.plane.render(self.surf_prog)

    def gen_look_at(self, eye, target, up):
        forward = np.array(target - eye)/np.linalg.norm(target - eye)
        side = np.cross(forward, up)/np.linalg.norm(np.cross(forward, up))
        up = np.cross(side, forward)/np.linalg.norm(np.cross(side, forward))

        view = np.array((
                (side[0], up[0], -forward[0], 0.),
                (side[1], up[1], -forward[1], 0.),
                (side[2], up[2], -forward[2], 0.),
                (-np.dot(side, eye), -np.dot(up, eye), np.dot(forward, eye), 1.0)
            ), dtype='f4')
        return view

