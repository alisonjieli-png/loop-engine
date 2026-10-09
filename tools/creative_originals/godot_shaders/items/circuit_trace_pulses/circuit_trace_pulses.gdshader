shader_type spatial;

uniform vec4 board_color : source_color = vec4(0.04, 0.22, 0.12, 1.0);
uniform vec4 copper_color : source_color = vec4(0.78, 0.6, 0.3, 1.0);
uniform vec4 pulse_color : source_color = vec4(0.3, 1.0, 0.9, 1.0);
uniform float cells : hint_range(2.0, 80.0) = 14.0;
uniform float trace_width : hint_range(0.02, 0.3) = 0.09;
uniform float via_radius : hint_range(0.05, 0.4) = 0.18;
uniform float pulse_speed : hint_range(0.0, 5.0) = 1.2;
uniform float pulse_share : hint_range(0.0, 1.0) = 0.45;
uniform float glow : hint_range(0.0, 6.0) = 2.5;

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

float segment_distance(vec2 p, vec2 a, vec2 b) {
	vec2 pa = p - a;
	vec2 ba = b - a;
	float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * h);
}

void fragment() {
	vec2 grid = UV * cells;
	vec2 cell = floor(grid);
	vec2 local = fract(grid);
	float kind = floor(hash21(cell) * 5.0);
	float distance_to_trace = 1.0;
	float along = 0.0;
	if (kind < 1.0) {
		distance_to_trace = abs(local.y - 0.5);
		along = local.x;
	} else if (kind < 2.0) {
		distance_to_trace = abs(local.x - 0.5);
		along = local.y;
	} else if (kind < 3.0) {
		distance_to_trace = min(segment_distance(local, vec2(0.0, 0.5), vec2(0.5, 0.5)),
								segment_distance(local, vec2(0.5, 0.5), vec2(0.5, 1.0)));
		along = local.x < 0.5 ? local.x * 0.5 : 0.25 + local.y * 0.5;
	} else if (kind < 4.0) {
		distance_to_trace = abs(length(local - 0.5) - via_radius * 0.6);
		along = atan(local.y - 0.5, local.x - 0.5) / TAU + 0.5;
	}
	float trace = 1.0 - smoothstep(trace_width * 0.5, trace_width * 0.5 + 0.02, distance_to_trace);
	float pad = (kind >= 3.0 && kind < 4.0) ? 1.0 - smoothstep(via_radius * 0.25, via_radius * 0.3, length(local - 0.5)) : 0.0;
	float active = step(hash21(cell + 31.0), pulse_share);
	float phase = fract(along - TIME * pulse_speed + hash21(cell + 7.0));
	float pulse = active * smoothstep(0.75, 1.0, phase) * trace;
	vec3 color = mix(board_color.rgb, copper_color.rgb, trace);
	color = mix(color, board_color.rgb * 0.3, pad);
	ALBEDO = color;
	METALLIC = trace * 0.8;
	ROUGHNESS = mix(0.5, 0.3, trace);
	EMISSION = pulse_color.rgb * pulse * glow;
}
