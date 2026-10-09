shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_nearest;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 line_color : source_color = vec4(0.05, 0.05, 0.08, 1.0);
uniform float line_width : hint_range(0.5, 4.0) = 1.0;
uniform float depth_sensitivity : hint_range(0.0, 50.0) = 8.0;
uniform float color_sensitivity : hint_range(0.0, 10.0) = 1.5;
uniform float threshold : hint_range(0.0, 2.0) = 0.3;
uniform float paper_mix : hint_range(0.0, 1.0) = 0.0;
uniform vec4 paper_color : source_color = vec4(0.96, 0.94, 0.88, 1.0);

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float inverse_depth(vec2 uv, mat4 inv_projection) {
	float raw = texture(depth_texture, uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(uv * 2.0 - 1.0, raw * 2.0 - 1.0);
#else
	vec3 ndc = vec3(uv * 2.0 - 1.0, raw);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return view.w / max(-view.z, 1e-4);
}

float luminance(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

void fragment() {
	vec2 step_uv = line_width / VIEWPORT_SIZE;
	float depth[9];
	float luma[9];
	int k = 0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 uv = SCREEN_UV + vec2(float(x), float(y)) * step_uv;
			depth[k] = inverse_depth(uv, INV_PROJECTION_MATRIX);
			luma[k] = luminance(texture(screen_texture, uv).rgb);
			k++;
		}
	}
	// Inverse depth is affine across a flat surface, so its Laplacian is zero there and large at edges.
	float laplacian = abs(depth[1] + depth[3] + depth[5] + depth[7] - 4.0 * depth[4]) / max(depth[4], 1e-5);
	float gx = (luma[2] + 2.0 * luma[5] + luma[8]) - (luma[0] + 2.0 * luma[3] + luma[6]);
	float gy = (luma[6] + 2.0 * luma[7] + luma[8]) - (luma[0] + 2.0 * luma[1] + luma[2]);
	float edge = max(laplacian * depth_sensitivity, length(vec2(gx, gy)) * color_sensitivity);
	float line = smoothstep(threshold, threshold * 1.5 + 0.05, edge);
	vec3 base = mix(texture(screen_texture, SCREEN_UV).rgb, paper_color.rgb, paper_mix);
	ALBEDO = mix(base, line_color.rgb, line * line_color.a);
}
