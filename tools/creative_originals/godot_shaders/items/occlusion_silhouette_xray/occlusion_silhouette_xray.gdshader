shader_type spatial;
render_mode depth_test_disabled, depth_draw_never, cull_back;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 albedo : source_color = vec4(0.8, 0.45, 0.2, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.6;
uniform vec4 xray_color : source_color = vec4(0.25, 0.75, 1.0, 1.0);
uniform float xray_fill : hint_range(0.0, 1.0) = 0.35;
uniform float xray_rim_power : hint_range(0.5, 8.0) = 2.0;
uniform float depth_bias : hint_range(0.0, 0.5) = 0.02;
uniform float pattern_density : hint_range(0.0, 400.0) = 120.0;

// Linear view depth of the opaque scene at a screen position (metres from the camera plane).
float scene_view_depth(vec2 screen_uv, mat4 inv_projection) {
	float raw = texture(depth_texture, screen_uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw * 2.0 - 1.0);
#else
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return -view.z / view.w;
}

void fragment() {
	float scene_depth = scene_view_depth(SCREEN_UV, INV_PROJECTION_MATRIX);
	float own_depth = -VERTEX.z;
	float hidden = step(scene_depth + depth_bias, own_depth);
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), xray_rim_power);
	float lines = 0.5 + 0.5 * sin((FRAGCOORD.x + FRAGCOORD.y) * pattern_density / 400.0 * TAU);
	vec3 visible_color = albedo.rgb;
	ALBEDO = mix(visible_color, vec3(0.0), hidden);
	ROUGHNESS = roughness;
	EMISSION = hidden * xray_color.rgb * (rim + xray_fill * (0.6 + 0.4 * lines));
	ALPHA = mix(1.0, clamp(rim + xray_fill, 0.0, 1.0), hidden);
}
