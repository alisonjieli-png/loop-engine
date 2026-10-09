shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform float focus_distance : hint_range(0.1, 100.0) = 2.4;
uniform float focus_range : hint_range(0.0, 20.0) = 0.4;
uniform float blur_falloff : hint_range(0.1, 20.0) = 2.5;
uniform float max_blur_pixels : hint_range(0.0, 32.0) = 9.0;
uniform int samples : hint_range(4, 64) = 32;
uniform bool show_focus = false;

// View-space position of the opaque scene at a screen position.
vec3 scene_view_position(vec2 screen_uv, mat4 inv_projection) {
	float raw = texture(depth_texture, screen_uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw * 2.0 - 1.0);
#else
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return view.xyz / view.w;
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float blur_radius(vec2 uv, mat4 inv_projection) {
	float depth = -scene_view_position(uv, inv_projection).z;
	float outside = max(abs(depth - focus_distance) - focus_range, 0.0);
	return clamp(outside / blur_falloff, 0.0, 1.0) * max_blur_pixels;
}

void fragment() {
	float center_radius = blur_radius(SCREEN_UV, INV_PROJECTION_MATRIX);
	vec3 total = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	float weight_total = 1.0;
	float golden_angle = 2.39996323;
	for (int i = 1; i < samples; i++) {
		float t = sqrt(float(i) / float(samples));
		float angle = float(i) * golden_angle;
		vec2 offset = vec2(cos(angle), sin(angle)) * t * max_blur_pixels;
		vec2 uv = SCREEN_UV + offset / VIEWPORT_SIZE;
		float sample_radius = blur_radius(uv, INV_PROJECTION_MATRIX);
		float reach = length(offset);
		float weight = clamp(min(center_radius, sample_radius) - reach + 1.0, 0.0, 1.0);
		total += textureLod(screen_texture, uv, 0.0).rgb * weight;
		weight_total += weight;
	}
	vec3 color = total / weight_total;
	if (show_focus) {
		color = mix(color, vec3(1.0, 0.2, 0.2), 0.5 * (1.0 - clamp(center_radius, 0.0, 1.0)));
	}
	ALBEDO = color;
}
