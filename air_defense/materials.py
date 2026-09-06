"""糖果材質：保留頂點色、柔和乘法陰影與真正的視距霧化。"""

_shader=None


def candy_shader():
    global _shader
    if _shader is not None:return _shader
    from ursina import Shader,Vec2,color
    light='''
uniform struct {
    vec4 position;
    vec3 color;
    vec3 attenuation;
    vec3 spotDirection;
    float spotCosCutoff;
    float spotExponent;
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;
} p3d_LightSource[1];
'''
    _shader=Shader(name='candy_shadow',language=Shader.GLSL,vertex='#version 150\n'+light+'''
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;
uniform vec2 texture_scale;
uniform vec2 texture_offset;
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 p3d_Color;
in vec2 p3d_MultiTexCoord0;
out vec4 tint;
out vec2 uv;
out vec3 view_position;
out vec3 view_normal;
out vec4 light_position;
void main() {
    gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;
    view_position=(p3d_ModelViewMatrix*p3d_Vertex).xyz;
    view_normal=p3d_NormalMatrix*p3d_Normal;
    light_position=p3d_LightSource[0].shadowViewMatrix*vec4(view_position,1.0);
    tint=p3d_Color;
    uv=p3d_MultiTexCoord0*texture_scale+texture_offset;
}
''',fragment='#version 150\n'+light+'''
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
uniform vec4 fog_color;
uniform float fog_start;
uniform float fog_end;
uniform int shadow_samples;
uniform float shadow_blur;
in vec4 tint;
in vec2 uv;
in vec3 view_position;
in vec3 view_normal;
in vec4 light_position;
out vec4 fragment_color;
void main() {
    vec4 base=texture(p3d_Texture0,uv)*tint*p3d_ColorScale;
    vec3 direction=normalize(p3d_LightSource[0].position.xyz-view_position*p3d_LightSource[0].position.w);
    vec3 normal=view_normal/max(length(view_normal),0.0001);
    float lightness=0.84+0.16*max(0.0,dot(normal,direction));
    vec3 shadow_uv=light_position.xyz/light_position.w;
    float shade=1.0;
    if (all(greaterThanEqual(shadow_uv,vec3(0))) && all(lessThanEqual(shadow_uv,vec3(1)))) {
        shade=0.0;
        for (int x=0;x<shadow_samples;x++) {
            for (int y=0;y<shadow_samples;y++) {
                vec4 coord=light_position;
                coord.xy+=(vec2(x,y)-float(shadow_samples-1)*0.5)*shadow_blur;
                coord.z+=0.003;
                shade+=textureProj(p3d_LightSource[0].shadowMap,coord);
            }
        }
        shade/=float(shadow_samples*shadow_samples);
    }
    base.rgb*=lightness*mix(0.72,1.0,shade);
    float fog=clamp((length(view_position)-fog_start)/max(1.0,fog_end-fog_start),0.0,1.0);
    fragment_color=vec4(mix(base.rgb,fog_color.rgb,fog),base.a);
}
''',default_input=dict(texture_scale=Vec2(1,1),texture_offset=Vec2(0,0),fog_color=color.hex('#b8dcf0'),fog_start=180.,fog_end=650.,shadow_samples=1,shadow_blur=.002))
    return _shader
