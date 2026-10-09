shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float k1 : hint_range(-1.0, 1.0) = 0.22;
uniform float k2 : hint_range(-1.0, 1.0) = 0.06;
uniform bool auto_fit = true;
uniform float zoom : hint_range(0.5, 2.0) = 1.0;
uniform float edge_darkening : hint_range(0.0, 1.0) = 0.3;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

vec2 distort(vec2 p) {
	float r2 = dot(p, p);
	return p * (1.0 + k1 * r2 + k2 * r2 * r2);
}

void fragment() {
	float aspect = VIEWPORT_SIZE.x / VIEWPORT_SIZE.y;
	vec2 p = (SCREEN_UV - 0.5) * vec2(aspect, 1.0);
	float corner = length(vec2(aspect, 1.0) * 0.5);
	float corner_scale = length(distort(vec2(corner, 0.0))) / corner;
	float fit = auto_fit && corner_scale > 1.0 ? 1.0 / corner_scale : 1.0;
	vec2 q = distort(p) * fit / zoom;
	vec2 uv = q / vec2(aspect, 1.0) + 0.5;
	float inside = step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);
	vec3 color = textureLod(screen_texture, uv, 0.0).rgb;
	float rim = 1.0 - edge_darkening * smoothstep(0.3, 0.75, length(p) / corner);
	ALBEDO = color * inside * rim;
}
