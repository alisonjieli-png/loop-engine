shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 field_color : source_color = vec4(0.3, 0.7, 1.0, 1.0);
uniform float base_strength : hint_range(0.0, 1.0) = 0.06;
uniform float rim_power : hint_range(0.5, 8.0) = 3.0;
uniform float rim_strength : hint_range(0.0, 4.0) = 1.1;
uniform float contact_width : hint_range(0.01, 2.0) = 0.18;
uniform float contact_strength : hint_range(0.0, 8.0) = 2.5;
uniform float band_frequency : hint_range(1.0, 60.0) = 14.0;
uniform float band_speed : hint_range(-4.0, 4.0) = 0.6;
uniform float band_strength : hint_range(0.0, 1.0) = 0.35;

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
	float surface_depth = -VERTEX.z;
	float gap = max(scene_depth - surface_depth, 0.0);
	float contact = 1.0 - smoothstep(0.0, contact_width, gap);
	float rim = pow(1.0 - abs(dot(NORMAL, VIEW)), rim_power);
	float bands = 0.5 + 0.5 * sin((UV.y * band_frequency + TIME * band_speed) * TAU);
	float strength = base_strength + rim * (rim_strength + bands * band_strength) + contact * contact_strength;
	ALBEDO = field_color.rgb * strength;
}
