shader_type spatial;
render_mode unshaded, cull_disabled;

uniform vec4 screen_color : source_color = vec4(0.0, 0.06, 0.03, 1.0);
uniform vec4 phosphor_color : source_color = vec4(0.25, 1.0, 0.45, 1.0);
uniform float sweep_speed : hint_range(-6.0, 6.0) = 1.2;
uniform float trail_angle : hint_range(0.1, 6.28) = 1.8;
uniform int range_rings : hint_range(1, 10) = 4;
uniform int spokes : hint_range(0, 24) = 8;
uniform float line_width : hint_range(0.001, 0.05) = 0.006;
uniform float blip_density : hint_range(0.0, 1.0) = 0.12;
uniform float blip_size : hint_range(0.005, 0.1) = 0.025;
uniform float blip_cells : hint_range(2.0, 40.0) = 10.0;

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

float angle_behind_sweep(float angle, float sweep) {
	return mod(sweep - angle, TAU);
}

void fragment() {
	vec2 p = (UV - 0.5) * 2.0;
	float radius = length(p);
	if (radius > 1.0) {
		discard;
	}
	float angle = atan(p.y, p.x);
	float sweep = mod(TIME * sweep_speed, TAU);
	float lag = angle_behind_sweep(angle, sweep);
	float trail = pow(1.0 - clamp(lag / trail_angle, 0.0, 1.0), 2.0);
	float ring_distance = abs(fract(radius * float(range_rings) + 0.5) - 0.5) / float(range_rings);
	float rings = 1.0 - smoothstep(0.0, line_width, ring_distance);
	float spoke_lines = 0.0;
	if (spokes > 0) {
		float spoke_angle = TAU / float(spokes);
		float nearest = abs(mod(angle + spoke_angle * 0.5, spoke_angle) - spoke_angle * 0.5);
		spoke_lines = 1.0 - smoothstep(0.0, line_width, nearest * radius);
	}
	vec2 grid = (p * 0.5 + 0.5) * blip_cells;
	vec2 cell = floor(grid);
	float blip = 0.0;
	if (hash21(cell) < blip_density) {
		vec2 center = (cell + 0.25 + hash22(cell + 3.0) * 0.5) / blip_cells * 2.0 - 1.0;
		float blip_angle = atan(center.y, center.x);
		float age = angle_behind_sweep(blip_angle, sweep) / TAU;
		float dot_mask = 1.0 - smoothstep(blip_size * 0.5, blip_size, length(p - center));
		blip = dot_mask * pow(1.0 - age, 3.0) * step(length(center), 0.95);
	}
	float edge = smoothstep(0.96, 1.0, radius);
	vec3 color = screen_color.rgb;
	color += phosphor_color.rgb * (0.25 * (rings + spoke_lines) + trail * 0.6 + blip * 1.5 + edge * 0.5);
	ALBEDO = color;
}
