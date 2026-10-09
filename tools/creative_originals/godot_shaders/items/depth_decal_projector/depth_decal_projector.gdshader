shader_type spatial;
render_mode unshaded, cull_front, depth_test_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform sampler2D decal_texture : source_color, hint_default_white, filter_linear;
uniform vec4 decal_color : source_color = vec4(0.95, 0.75, 0.1, 1.0);
uniform vec4 accent_color : source_color = vec4(0.08, 0.08, 0.08, 1.0);
uniform float opacity : hint_range(0.0, 1.0) = 0.9;
uniform float angle_fade : hint_range(0.0, 1.0) = 0.4;
uniform float edge_fade : hint_range(0.0, 0.5) = 0.05;
uniform int stripe_count : hint_range(0, 24) = 10;
uniform float ring_width : hint_range(0.0, 0.5) = 0.12;

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

void fragment() {
	vec3 view_position = scene_view_position(SCREEN_UV, INV_PROJECTION_MATRIX);
	vec3 world = (INV_VIEW_MATRIX * vec4(view_position, 1.0)).xyz;
	vec3 local = (inverse(MODEL_MATRIX) * vec4(world, 1.0)).xyz;
	if (any(greaterThan(abs(local), vec3(0.5)))) {
		discard;
	}
	vec3 surface_normal = normalize(cross(dFdy(world), dFdx(world)));
	vec3 box_up = normalize(MODEL_MATRIX[1].xyz);
	float facing = abs(dot(surface_normal, box_up));
	float angle_mask = smoothstep(angle_fade * 0.5, angle_fade, facing);
	vec2 uv = local.xz + 0.5;
	vec2 centered = uv - 0.5;
	float radius = length(centered) * 2.0;
	float ring = step(1.0 - ring_width, radius) * step(radius, 1.0);
	float disc = step(radius, 1.0 - ring_width * 1.5);
	float angle = atan(centered.y, centered.x);
	float stripes = stripe_count > 0 ? step(0.5, fract((centered.x + centered.y) * float(stripe_count) * 0.5)) : 0.0;
	vec3 emblem = mix(decal_color.rgb, accent_color.rgb, max(ring, disc * stripes));
	float coverage = max(ring, disc);
	vec4 texel = texture(decal_texture, uv);
	vec3 edge = smoothstep(vec3(0.5), vec3(0.5 - edge_fade), abs(local));
	float alpha = coverage * texel.a * opacity * angle_mask * edge.x * edge.y * edge.z;
	ALBEDO = emblem * texel.rgb;
	ALPHA = alpha;
}
