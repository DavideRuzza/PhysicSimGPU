#version 460

uniform mat4 proj;
uniform mat4 view;
uniform mat4 model;

#ifdef VERTEX_SHADER

in vec3 in_position;
in vec2 in_texcoord_0;
in vec3 in_normal;

out vec2 uv;
out vec3 N;

void main(){
    gl_Position = proj*view*model*vec4(in_position, 1.0);
    uv = in_texcoord_0;
    N = normalize(in_normal);
}

#elif FRAGMENT_SHADER

in vec2 uv;
in vec3 N;
layout(location=0) out vec4 fragColor;

void main(){
    fragColor = vec4(N, 0.0);
}

#endif

