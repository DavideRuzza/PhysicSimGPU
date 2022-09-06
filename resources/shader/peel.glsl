#version 460

uniform mat4 proj;
uniform mat4 view;
uniform mat4 model;

uniform float size; 
uniform float out_lay; // output layer
uniform float in_lay; // input layer
uniform float n_lay; // tot num of layers

uniform float water_surf;
uniform float dx;
uniform float dy;

layout(binding=0) uniform sampler2D depthTex;
layout(binding=1) uniform sampler2D peelTex;

#ifdef VERTEX_SHADER

in vec3 in_position;
in vec2 in_texcoord_0;
in vec3 in_normal;

// out vec2 uv;
out vec3 N;
out vec3 pos;

void main(){
    gl_Position = proj*view*model*vec4(in_position, 1.0);
    pos = vec3(model*vec4(in_position, 1.0));
    // uv = in_texcoord_0;
    N = mat3(transpose(inverse(model)))*normalize(in_normal);
}

#elif FRAGMENT_SHADER

// in vec2 uv;
in vec3 N;
in vec3 pos;

layout(location=0) out vec4 fragOut;
layout(location=1) out vec4 fragOut1;
layout(location=2) out vec4 fragOut2;
layout(location=3) out vec4 fragOut3;

void main(){


    vec2 UV = gl_FragCoord.xy/size;
    UV.x = UV.x/n_lay - (out_lay-in_lay)/n_lay;

    float depth = texture(depthTex, UV).r;
    if (gl_FragCoord.z-1e-5 <= depth){
        discard;
    } 

    fragOut = vec4(N, 1.0);
    float c = sign(N.z) * pos.z;
    fragOut1 = vec4(c*pos, c) *dx*dy; // (rx, ry, rz, V)
    fragOut2 = pos.x * vec4(c*pos, 0.0) *dx*dy; // (Ixx, Ixy, Ixz, .)
    fragOut3 = c * vec4(pos.y*pos.y, pos.y*pos.z, pos.z*pos.z, 0.0) *dx*dy; // (Iyy, Iyz, Izz, .)
    
    
}
#endif

