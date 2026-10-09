shader_type canvas_item;

uniform vec4 core_color : source_color = vec4(1.0, 0.95, 0.95, 1.0);
uniform vec4 beam_color : source_color = vec4(1.0, 0.15, 0.3, 1.0);
uniform float core_width : hint_range(0.0, 0.3) = 0.04;
uniform float glow_width : hint_range(0.0, 0.5) = 0.18;
uniform float flicker : hint_range(0.0, 1.0) = 0.3;
uniform float pulse_speed : hint_range(-10.0, 10.0) = 3.0;
uniform float pulse_spacing : hint_range(0.05, 1.0) = 0.2;
uniform float flare_size : hint_range(0.0, 0.5) = 0.18;
uniform float impact_size : hint_range(0.0, 0.5) = 0.12;

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

float value_noise(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float a = hash21(cell);
	float b = hash21(cell + vec2(1.0, 0.0));
	float c = hash21(cell + vec2(0.0, 1.0));
	float d = hash21(cell + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p, int octaves) {
	float total = 0.0;
	float amplitude = 0.5;
	float norm = 0.0;
	mat2 turn = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
	for (int i = 0; i < octaves; i++) {
		total += amplitude * value_noise(p);
		norm += amplitude;
		p = turn * p * 2.03 + vec2(17.13, 9.71);
		amplitude *= 0.5;
	}
	return total / norm;
}

void fragment() {
	float x = UV.x;
	float y = UV.y - 0.5;
	float wobble = 1.0 + (value_noise(vec2(x * 20.0 - TIME * 12.0, 0.5)) - 0.5) * flicker;
	float d = abs(y) / wobble;
	float core = 1.0 - smoothstep(core_width * 0.3, core_width * 0.5, d);
	float glow = exp(-d / max(glow_width, 1e-4) * 4.0);
	float pulse = smoothstep(0.7, 1.0, fract(x / pulse_spacing - TIME * pulse_speed)) * glow * 0.6;
	vec2 emitter = vec2(x * 1.5, y);
	float flare = exp(-length(emitter) / max(flare_size, 1e-4) * 3.0);
	vec2 impact = vec2((x - 1.0) * 1.5, y);
	float sparks = step(0.8, value_noise(vec2(atan(impact.y, impact.x) * 6.0, TIME * 20.0)));
	float hit = exp(-length(impact) / max(impact_size, 1e-4) * 3.0) * (0.7 + 0.6 * sparks);
	vec3 color = beam_color.rgb * (glow + pulse + flare + hit) + core_color.rgb * (core + flare * 0.6 + hit * 0.5);
	float alpha = clamp(core + glow + flare + hit, 0.0, 1.0);
	COLOR = vec4(color, alpha);
}
