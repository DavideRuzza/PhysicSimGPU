from ssl import SSLEOFError
import sys
import moderngl as mgl
import moderngl_window as mglw
from moderngl_window.geometry import quad_fs
from rigid_body import BouyantRigidBody
from camera import OrbitCamera
from pyrr import Matrix44 as m44
import numpy as np


class Window(OrbitCamera):

    title = "Test"
    window_size = (1024, 512)
    gl_version = (4, 6, 0)
    aspect_ratio = window_size[0]/window_size[1]
    resource_dir='resources/'

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)


        self.debug_prog = self.load_program("shader/debug.glsl")
        self.simp3d_prog = self.load_program("shader/simple3d.glsl")

        self.proj_mat = m44.perspective_projection(40, self.aspect_ratio, 0.1, 100)

        self.simp3d_prog['proj'].write(self.proj_mat.astype('f4'))
        self.simp3d_prog['view'].write(self.view.astype('f4'))
        

        self.quad = quad_fs()


        self.ctx.enable(mgl.DEPTH_TEST)

        # test ocean surf textures
        with open("surf.txt", "rb") as f:
            surf = f.read()
        with open("norm.txt", "rb") as f:
            norm = f.read()

        self.surf_tex = self.ctx.texture(size=(256, 256), components=4, data=surf, dtype='f4')
        self.norm_tex = self.ctx.texture(size=(256, 256), components=4, data=norm, dtype='f4')

        self.surf_size = 20
        self.wave_scale = 6
        self.choppy = 10
        
        self.surf_prog = self.load_program("shader/ocean_surf.glsl")
        self.ocean = self.load_scene("scenes/surface.obj").meshes[0].vao

        self.bunny = BouyantRigidBody(self.ctx, "scenes/bunny.obj", rho=0.4)
        self.bunny.load_surface(self.surf_prog, self.ocean, self.surf_tex, 
                                self.norm_tex, self.choppy, self.wave_scale, self.surf_size)

        self.bunny.pos[2] += 2.

    def render(self, t, dt):
        
        
        self.bunny.update_bouyancy(dt)


        self.wnd.fbo.use()
        self.ctx.clear(*[0.2]*3)

        self.ctx.enable(mgl.DEPTH_TEST)
        
        self.bunny.render_surf(self.proj_mat, self.view)
        self.simp3d_prog['model'].write(m44.identity().astype('f4'))
        self.quad.render(self.simp3d_prog)
        self.simp3d_prog['model'].write(self.bunny.gen_model_matrix().astype('f4'))
        self.bunny.vao.render(self.simp3d_prog)

        self.ctx.disable(mgl.DEPTH_TEST)
        self.wnd.fbo.viewport = 0, 0, 128*self.bunny.n_layer, 128
        self.bunny.peel_tex.use(0)
        self.quad.render(self.debug_prog)
        self.wnd.fbo.viewport = 0, 0, *self.window_size

        self.simp3d_prog['view'].write(self.view.astype('f4'))
        

Window.run()
