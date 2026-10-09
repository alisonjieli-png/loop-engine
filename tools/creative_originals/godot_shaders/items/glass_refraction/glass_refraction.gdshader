shader_type spatial;
render_mode unshaded, cull_back, depth_draw_always, shadows_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform vec4 tint : source_color = vec4(0.85, 0.95, 1.0, 1.0);
uniform float refraction_strength : hint_range(0.0, 0.3) = 0.08;
uniform float dispersion : hint_range(0.0, 1.0) = 0.25;
uniform float frost : hint_range(0.0, 6.0) = 0.0;
uniform float fresnel_power : hint_range(0.5, 8.0) = 4.0;
uniform float fresnel_strength : hint_range(0.0, 1.0) = 0.6;
uniform vec4 reflection_color : source_color = vec4(0.9, 0.95, 1.0, 1.0);
uniform float thickness_tint : hint_range(0.0, 1.0) = 0.35;

void fragment() {
	vec3 n = normalize(NORMAL);
	float facing = clamp(dot(n, VIEW), 0.0, 1.0);
	float thickness = mix(1.0, 0.4, facing);
	vec2 offset = n.xy * refraction_strength * thickness;
	float r = textureLod(screen_texture, SCREEN_UV - offset * (1.0 + dispersion), frost).r;
	float g = textureLod(screen_texture, SCREEN_UV - offset, frost).g;
	float b = textureLod(screen_texture, SCREEN_UV - offset * (1.0 - dispersion), frost).b;
	vec3 behind = vec3(r, g, b);
	behind *= mix(vec3(1.0), tint.rgb, thickness_tint * thickness + (1.0 - thickness_tint) * 0.5);
	float fresnel = pow(1.0 - facing, fresnel_power) * fresnel_strength;
	ALBEDO = mix(behind, reflection_color.rgb, fresnel);
}
