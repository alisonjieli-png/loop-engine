shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 edge_color : source_color = vec4(0.3, 0.8, 1.0, 1.0);
uniform vec4 fill_color : source_color = vec4(0.1, 0.35, 0.8, 1.0);
uniform float hex_scale : hint_range(2.0, 60.0) = 14.0;
uniform float edge_width : hint_range(0.0, 0.3) = 0.06;
uniform float pulse_speed : hint_range(-4.0, 4.0) = 0.6;
uniform float pulse_spacing : hint_range(0.1, 4.0) = 1.2;
uniform float flicker_rate : hint_range(0.0, 20.0) = 3.0;
uniform float flicker_share : hint_range(0.0, 1.0) = 0.1;
uniform float rim_strength : hint_range(0.0, 2.0) = 0.8;

varying vec3 object_position;

// MurmurHash3 32-bit finalizer used as an integer hash.
uint fmix32(uint h) {
	h ^= h >> 16u;
	h *= 0x85ebca6bu;
	h ^= h >> 13u;
	h *= 0xc2b2ae35u;
	h ^= h >> 16u;
	return h;
}

uint lattice2(vec2 p) {
	ivec2 c = ivec2(floor(p));
	return fmix32(uint(c.x) * 73856093u ^ uint(c.y) * 19349663u);
}

float hash21(vec2 p) {
	return float(lattice2(p)) / 4294967295.0;
}

vec2 hash22(vec2 p) {
	uint h = lattice2(p);
	return vec2(float(h & 0xffffu), float(h >> 16u)) / 65535.0;
}

// Nearest hexagon centre on a pointy-top hex lattice and the offset from it.
vec4 hex_cell(vec2 p) {
	vec2 spacing = vec2(1.0, 1.7320508);
	vec2 a = mod(p, spacing) - spacing * 0.5;
	vec2 b = mod(p - spacing * 0.5, spacing) - spacing * 0.5;
	vec2 local = dot(a, a) < dot(b, b) ? a : b;
	return vec4(local, p - local);
}

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	vec4 hex = hex_cell(UV * vec2(hex_scale * 2.0, hex_scale));
	vec2 local = abs(hex.xy);
	float distance_to_edge = 0.5 - max(dot(local, vec2(0.5, 0.8660254)), local.x);
	float edge = 1.0 - smoothstep(0.0, edge_width, distance_to_edge);
	float wave = fract(object_position.y / pulse_spacing - TIME * pulse_speed);
	float pulse = smoothstep(0.0, 0.15, wave) * (1.0 - smoothstep(0.15, 0.5, wave));
	float slot = floor(TIME * flicker_rate);
	float flicker = step(1.0 - flicker_share, hash21(hex.zw * 3.7 + vec2(slot, slot * 1.3)));
	float rim = pow(1.0 - abs(dot(NORMAL, VIEW)), 2.5) * rim_strength;
	float fill = 0.05 + pulse * 0.5 + flicker * 0.35;
	ALBEDO = edge_color.rgb * edge * (0.4 + pulse + rim) + fill_color.rgb * (fill + rim * 0.5);
}
