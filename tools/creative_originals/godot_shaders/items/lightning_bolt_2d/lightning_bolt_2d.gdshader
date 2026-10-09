shader_type canvas_item;

uniform vec4 core_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 glow_color : source_color = vec4(0.55, 0.6, 1.0, 1.0);
uniform float jaggedness : hint_range(0.0, 0.5) = 0.18;
uniform float core_width : hint_range(0.001, 0.05) = 0.006;
uniform float glow_width : hint_range(0.01, 0.5) = 0.08;
uniform float strike_rate : hint_range(0.1, 10.0) = 1.5;
uniform float visible_share : hint_range(0.05, 1.0) = 0.6;
uniform float branch_amount : hint_range(0.0, 1.0) = 0.6;
uniform float start_x : hint_range(0.0, 1.0) = 0.45;
uniform float end_x : hint_range(0.0, 1.0) = 0.55;

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

float bolt_offset(float y, float seed) {
	float total = 0.0;
	float amplitude = jaggedness;
	float frequency = 3.0;
	for (int i = 0; i < 5; i++) {
		total += (value_noise(vec2(y * frequency, seed + float(i) * 13.0)) - 0.5) * amplitude;
		amplitude *= 0.5;
		frequency *= 2.2;
	}
	return total * sin(y * PI);
}

void fragment() {
	float strike = floor(TIME * strike_rate);
	float phase = fract(TIME * strike_rate);
	float seed = hash21(vec2(strike, 3.0)) * 100.0;
	float y = UV.y;
	float main_x = mix(start_x, end_x, y) + bolt_offset(y, seed);
	float d = abs(UV.x - main_x);
	float branch_start = 0.3 + hash21(vec2(strike, 5.0)) * 0.3;
	float branch_y = (y - branch_start) / max(1.0 - branch_start, 1e-3);
	if (branch_y > 0.0 && branch_y < 0.6) {
		float origin = mix(start_x, end_x, branch_start) + bolt_offset(branch_start, seed);
		float direction = hash21(vec2(strike, 7.0)) > 0.5 ? 1.0 : -1.0;
		float branch_x = origin + direction * branch_y * 0.35 + bolt_offset(branch_y, seed + 40.0) * 0.6;
		float fade = (1.0 - branch_y / 0.6) * branch_amount;
		d = min(d, abs(UV.x - branch_x) / max(fade, 1e-3));
	}
	float visible = step(phase, visible_share) * (0.6 + 0.4 * step(0.5, fract(phase * 23.0)));
	float core = 1.0 - smoothstep(core_width * 0.5, core_width, d);
	float glow = exp(-d / glow_width * 3.0);
	vec3 color = core_color.rgb * core + glow_color.rgb * glow * 0.8;
	COLOR = vec4(color, clamp(core + glow * 0.8, 0.0, 1.0) * visible);
}
