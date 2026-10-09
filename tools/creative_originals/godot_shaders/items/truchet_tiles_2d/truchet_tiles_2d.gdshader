shader_type canvas_item;

uniform vec4 line_color : source_color = vec4(0.95, 0.85, 0.55, 1.0);
uniform vec4 background_color : source_color = vec4(0.1, 0.12, 0.2, 1.0);
uniform vec4 flow_color : source_color = vec4(1.0, 0.4, 0.3, 1.0);
uniform float cells : hint_range(2.0, 60.0) = 10.0;
uniform float line_width : hint_range(0.01, 0.4) = 0.12;
uniform float flow_speed : hint_range(-4.0, 4.0) = 1.0;
uniform float flow_spacing : hint_range(0.1, 2.0) = 0.5;
uniform int seed : hint_range(0, 1000) = 3;

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

void fragment() {
	vec2 grid = UV * cells;
	vec2 cell = floor(grid);
	vec2 local = fract(grid);
	float flip = step(0.5, hash21(cell + float(seed) * 13.0));
	if (flip > 0.5) {
		local.x = 1.0 - local.x;
	}
	float d1 = abs(length(local) - 0.5);
	float d2 = abs(length(local - 1.0) - 0.5);
	float d = min(d1, d2);
	vec2 corner_vector = d1 < d2 ? local : local - 1.0;
	float arc = atan(abs(corner_vector.y), abs(corner_vector.x)) / (PI * 0.5);
	float parity = mod(cell.x + cell.y + flip, 2.0);
	float along = (parity > 0.5 ? arc : 1.0 - arc) + cell.x + cell.y;
	float width = fwidth(d);
	float line = 1.0 - smoothstep(line_width * 0.5 - width, line_width * 0.5 + width, d);
	float pulse = smoothstep(0.75, 1.0, fract(along / flow_spacing - TIME * flow_speed));
	vec3 color = mix(background_color.rgb, mix(line_color.rgb, flow_color.rgb, pulse), line);
	COLOR = vec4(color, 1.0);
}
