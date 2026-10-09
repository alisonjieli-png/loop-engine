shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform vec4 lift : source_color = vec4(0.04, 0.02, 0.08, 1.0);
uniform vec4 gamma : source_color = vec4(0.5, 0.5, 0.52, 1.0);
uniform vec4 gain : source_color = vec4(1.0, 0.96, 0.88, 1.0);
uniform float contrast : hint_range(0.5, 2.0) = 1.1;
uniform float saturation : hint_range(0.0, 2.0) = 1.1;
uniform float vibrance : hint_range(-1.0, 1.0) = 0.2;
uniform float temperature : hint_range(-1.0, 1.0) = 0.15;
uniform float tint : hint_range(-1.0, 1.0) = 0.0;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	color *= vec3(1.0 + temperature * 0.1, 1.0 + tint * 0.1, 1.0 - temperature * 0.1);
	color = gain.rgb * (color + lift.rgb * (1.0 - color));
	vec3 exponent = pow(vec3(2.0), (vec3(0.5) - gamma.rgb) * 2.0);
	color = pow(max(color, vec3(0.0)), exponent);
	color = (color - 0.5) * contrast + 0.5;
	float l = luminance(color);
	color = mix(vec3(l), color, saturation);
	float chroma = max(max(color.r, color.g), color.b) - min(min(color.r, color.g), color.b);
	color = mix(vec3(l), color, 1.0 + vibrance * (1.0 - chroma));
	ALBEDO = clamp(color, 0.0, 1.0);
}
