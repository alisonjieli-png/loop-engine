shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float focus_center : hint_range(0.0, 1.0) = 0.55;
uniform float focus_width : hint_range(0.0, 0.8) = 0.12;
uniform float blur_ramp : hint_range(0.01, 1.0) = 0.3;
uniform float max_blur_pixels : hint_range(0.0, 24.0) = 8.0;
uniform float saturation : hint_range(0.0, 2.0) = 1.35;
uniform float contrast : hint_range(0.5, 2.0) = 1.1;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	float away = max(abs(SCREEN_UV.y - focus_center) - focus_width, 0.0);
	float blur = smoothstep(0.0, blur_ramp, away) * max_blur_pixels;
	vec3 total = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	float count = 1.0;
	for (int i = 1; i < 16; i++) {
		float t = sqrt(float(i) / 16.0);
		float angle = float(i) * 2.39996323;
		vec2 offset = vec2(cos(angle), sin(angle)) * t * blur / VIEWPORT_SIZE;
		total += textureLod(screen_texture, SCREEN_UV + offset, 0.0).rgb;
		count += 1.0;
	}
	vec3 color = total / count;
	color = (color - 0.5) * contrast + 0.5;
	color = mix(vec3(luminance(color)), color, saturation);
	ALBEDO = clamp(color, 0.0, 1.0);
}
