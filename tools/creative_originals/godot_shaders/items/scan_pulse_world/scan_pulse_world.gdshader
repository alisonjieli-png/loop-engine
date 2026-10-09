shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 pulse_color : source_color = vec4(0.25, 1.0, 0.85, 1.0);
uniform float center_x : hint_range(-50.0, 50.0) = 0.0;
uniform float center_y : hint_range(-50.0, 50.0) = 0.0;
uniform float center_z : hint_range(-50.0, 50.0) = 0.0;
uniform float pulse_speed : hint_range(0.1, 50.0) = 4.0;
uniform float pulse_period : hint_range(0.5, 20.0) = 3.0;
uniform float ring_width : hint_range(0.01, 2.0) = 0.15;
uniform float trail_length : hint_range(0.0, 10.0) = 2.5;
uniform float grid_size : hint_range(0.05, 5.0) = 0.5;
uniform float max_distance : hint_range(1.0, 500.0) = 100.0;

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

void fragment() {
	vec3 scene = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 view_position = scene_view_position(SCREEN_UV, INV_PROJECTION_MATRIX);
	vec3 world = (INV_VIEW_MATRIX * vec4(view_position, 1.0)).xyz;
	float distance_to_center = length(world - vec3(center_x, center_y, center_z));
	float radius = mod(TIME, pulse_period) * pulse_speed;
	float behind = radius - distance_to_center;
	float ring = 1.0 - smoothstep(0.0, ring_width, abs(behind));
	float trail = step(0.0, behind) * (1.0 - smoothstep(0.0, trail_length, behind));
	vec3 g = abs(fract(world / grid_size - 0.5) - 0.5) / max(fwidth(world / grid_size), vec3(1e-4));
	float grid = 1.0 - clamp(min(min(g.x, g.y), g.z) - 0.5, 0.0, 1.0);
	float valid = step(length(view_position), max_distance);
	float glow = (ring * 1.5 + trail * (0.15 + grid * 0.6)) * valid;
	ALBEDO = scene + pulse_color.rgb * glow;
}
