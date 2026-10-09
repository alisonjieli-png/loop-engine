shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D gradient : source_color, filter_linear, repeat_disable;
uniform float contrast : hint_range(0.2, 3.0) = 1.2;
uniform float offset : hint_range(-0.5, 0.5) = 0.0;
uniform float mix_amount : hint_range(0.0, 1.0) = 1.0;
uniform bool reverse = false;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	float l = clamp((luminance(color) - 0.5) * contrast + 0.5 + offset, 0.0, 1.0);
	if (reverse) {
		l = 1.0 - l;
	}
	vec3 mapped = texture(gradient, vec2(clamp(l, 0.005, 0.995), 0.5)).rgb;
	ALBEDO = mix(color, mapped, mix_amount);
}
