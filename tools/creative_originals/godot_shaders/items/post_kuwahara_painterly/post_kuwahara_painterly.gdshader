shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_nearest;
uniform int radius : hint_range(1, 8) = 4;
uniform float sample_spacing : hint_range(0.5, 3.0) = 1.0;
uniform float saturation : hint_range(0.0, 2.0) = 1.2;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 texel = sample_spacing / VIEWPORT_SIZE;
	vec3 means[4];
	vec3 squares[4];
	for (int q = 0; q < 4; q++) {
		means[q] = vec3(0.0);
		squares[q] = vec3(0.0);
	}
	for (int y = -radius; y <= radius; y++) {
		for (int x = -radius; x <= radius; x++) {
			vec3 c = texture(screen_texture, SCREEN_UV + vec2(float(x), float(y)) * texel).rgb;
			if (x <= 0 && y <= 0) { means[0] += c; squares[0] += c * c; }
			if (x >= 0 && y <= 0) { means[1] += c; squares[1] += c * c; }
			if (x <= 0 && y >= 0) { means[2] += c; squares[2] += c * c; }
			if (x >= 0 && y >= 0) { means[3] += c; squares[3] += c * c; }
		}
	}
	float count = float((radius + 1) * (radius + 1));
	vec3 best = means[0] / count;
	float best_variance = 1e9;
	for (int q = 0; q < 4; q++) {
		vec3 mean = means[q] / count;
		vec3 variance = abs(squares[q] / count - mean * mean);
		float total = variance.r + variance.g + variance.b;
		if (total < best_variance) {
			best_variance = total;
			best = mean;
		}
	}
	float l = dot(best, vec3(0.299, 0.587, 0.114));
	ALBEDO = mix(vec3(l), best, saturation);
}
