#version 460

uniform mat4 proj;
uniform mat4 view;
uniform mat4 model;
uniform mat4 scale_model;

uniform float choppy;
uniform float wave_scale;

layout(binding=0) uniform sampler2D surf;
layout(binding=1) uniform sampler2D norm;


// peel prog
uniform float dx;
uniform float dy;

uniform int intersect;

layout(binding=2) uniform sampler2D depth;
layout(binding=3) uniform sampler2D norm_peel;

uniform float size; 
uniform float out_lay; // output layer
uniform float in_lay; // input layer
uniform float n_lay; // tot num of layers


#ifdef VERTEX_SHADER

in vec3 in_position;
in vec2 in_texcoord_0;

out vec2 uv;
out vec3 pos;

void main(){

    uv = in_texcoord_0;

    vec3 delta = texture(surf, in_texcoord_0).xyz;
    // color = vec3(delta);
    delta.xy *= -choppy;
    delta.z *= wave_scale;
    pos = vec3(scale_model*model*vec4(in_position, 1.0)+model*vec4(delta, 1.0));

    gl_Position = proj*view*(scale_model*model*vec4(in_position, 1.0)+model*vec4(delta, 1.0));
}

#elif FRAGMENT_SHADER

in vec2 uv;
in vec3 pos;

layout(location=0) out vec4 fragColor;
layout(location=1) out vec4 fragOut1;
layout(location=2) out vec4 fragOut2;
layout(location=3) out vec4 fragOut3;

void main(){
    
    vec3 N = texture(norm, uv).xyz;

    if (intersect==1){
        vec2 UV = gl_FragCoord.xy/size;
        UV.x = UV.x/n_lay - (out_lay-in_lay)/n_lay;

        vec3 peel_norm = texture(norm_peel, UV).xyz;
        float peel_depth = texture(depth, UV).r;
        // fragColor = vec4(peel_norm, 0.0);
        if (peel_norm.z > 0. || peel_depth > 0.999){
            discard;
        }

    }
    fragColor = vec4(N, 1.0);
    float c = sign(N.z) * pos.z;
    fragOut1 = vec4(c*pos, c) *dx*dy; // (rx, ry, rz, V)
    fragOut2 = pos.x * vec4(c*pos/vec3(1., 1., 2.), 0.0) *dx*dy; // (Ixx, Ixy, Ixz, .)
    fragOut3 = c * vec4(pos.y*pos.y, pos.y*pos.z/2., pos.z*pos.z/3., 0.0) *dx*dy; // (Iyy, Iyz, Izz, .)



}

#endif

