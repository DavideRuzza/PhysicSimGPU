#version 460

uniform mat4 proj;
uniform mat4 view;
uniform mat4 model;
uniform mat4 scale_model;

uniform float choppy;
uniform float wave_scale;

layout(binding=0) uniform sampler2D surf;
layout(binding=1) uniform sampler2D norm;

#ifdef VERTEX_SHADER

in vec3 in_position;
in vec2 in_texcoord_0;
in vec3 in_normal;

out vec2 uv;
out vec3 N;

void main(){

    uv = in_texcoord_0;

    vec3 delta = texture(surf, uv).xyz;
    delta.xy *= -choppy;
    delta.z *= wave_scale;
    gl_Position = proj*view*(scale_model*model*vec4(in_position, 1.0)+model*vec4(delta, 1.0));
    N = normalize(texture(norm, uv).xyz);
}

#elif FRAGMENT_SHADER

in vec2 uv;
in vec3 N;
layout(location=0) out vec4 fragColor;

void main(){
    fragColor = vec4(N, 0.0);
}

#endif

