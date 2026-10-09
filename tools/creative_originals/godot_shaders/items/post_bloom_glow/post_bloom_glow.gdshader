shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float threshold : hint_range(0.0, 1.0) = 0.62;
uniform float knee : hint_range(0.0, 0.5) = 0.15;
uniform float intensity : hint_range(0.0, 4.0) = 1.3;
uniform int levels : hint_range(1, 6) = 5;
uniform float spread : hint_range(0.0, 1.0) = 0.6;
uniform vec4 tint : source_color = vec4(1.0, 0.92, 0.8, 1.0);

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

vec3 bright_part(vec3 color) {
	float l = luminance(color);
	float soft = clamp(l - threshold + knee, 0.0, 2.0 * knee);
	soft = soft * soft / (4.0 * knee + 1e-4);
	float contribution = max(soft, l - threshold) / max(l, 1e-4);
	return color * contribution;
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 glow = vec3(0.0);
	float weight_total = 0.0;
	for (int i = 1; i <= levels; i++) {
		float weight = pow(spread, float(i - 1));
		vec2 jitter = vec2(1.0, -1.0) * pow(2.0, float(i)) / VIEWPORT_SIZE * 0.5;
		vec3 sample_a = textureLod(screen_texture, SCREEN_UV + jitter, float(i)).rgb;
		vec3 sample_b = textureLod(screen_texture, SCREEN_UV - jitter, float(i)).rgb;
		glow += bright_part((sample_a + sample_b) * 0.5) * weight;
		weight_total += weight;
	}
	glow /= max(weight_total, 1e-4);
	ALBEDO = color + glow * tint.rgb * intensity;
}
