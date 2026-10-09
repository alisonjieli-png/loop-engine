shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform sampler2D sprite : source_color, hint_default_white, filter_linear;
uniform vec4 tint : source_color = vec4(0.8, 0.82, 0.88, 0.8);
uniform float fade_distance : hint_range(0.01, 4.0) = 0.6;
uniform float camera_fade_near : hint_range(0.0, 5.0) = 0.3;
uniform float camera_fade_far : hint_range(0.0, 10.0) = 0.8;
uniform float fade_power : hint_range(0.25, 4.0) = 1.0;

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
	vec4 texel = texture(sprite, UV);
	float scene_depth = scene_view_depth(SCREEN_UV, INV_PROJECTION_MATRIX);
	float gap = scene_depth + VERTEX.z;
	float soft = pow(clamp(gap / fade_distance, 0.0, 1.0), fade_power);
	float near = smoothstep(camera_fade_near, camera_fade_far, -VERTEX.z);
	ALBEDO = texel.rgb * tint.rgb;
	ALPHA = texel.a * tint.a * soft * near;
}
