shader_type spatial;

uniform vec4 paint_color : source_color = vec4(0.2, 0.42, 0.35, 1.0);
uniform vec4 metal_color : source_color = vec4(0.62, 0.62, 0.64, 1.0);
uniform vec4 rust_color : source_color = vec4(0.48, 0.22, 0.08, 1.0);
uniform vec4 rust_dark : source_color = vec4(0.22, 0.1, 0.05, 1.0);
uniform float scale : hint_range(0.5, 20.0) = 4.0;
uniform float chipping : hint_range(0.0, 1.0) = 0.35;
uniform float rust_spread : hint_range(0.0, 0.5) = 0.12;
uniform float streak_amount : hint_range(0.0, 1.0) = 0.5;
uniform float streak_length : hint_range(0.5, 10.0) = 3.0;

varying vec3 world_position;

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

float hash31(vec3 p) {
	ivec3 c = ivec3(floor(p));
	return float(fmix32(uint(c.x) * 73856093u ^ uint(c.y) * 19349663u ^ uint(c.z) * 83492791u)) / 4294967295.0;
}

float value_noise3(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	float n000 = hash31(cell);
	float n100 = hash31(cell + vec3(1.0, 0.0, 0.0));
	float n010 = hash31(cell + vec3(0.0, 1.0, 0.0));
	float n110 = hash31(cell + vec3(1.0, 1.0, 0.0));
	float n001 = hash31(cell + vec3(0.0, 0.0, 1.0));
	float n101 = hash31(cell + vec3(1.0, 0.0, 1.0));
	float n011 = hash31(cell + vec3(0.0, 1.0, 1.0));
	float n111 = hash31(cell + vec3(1.0, 1.0, 1.0));
	float x00 = mix(n000, n100, u.x);
	float x10 = mix(n010, n110, u.x);
	float x01 = mix(n001, n101, u.x);
	float x11 = mix(n011, n111, u.x);
	return mix(mix(x00, x10, u.y), mix(x01, x11, u.y), u.z);
}

float fbm3(vec3 p, int octaves) {
	float total = 0.0;
	float amplitude = 0.5;
	float norm = 0.0;
	for (int i = 0; i < octaves; i++) {
		total += amplitude * value_noise3(p);
		norm += amplitude;
		p = p * 2.07 + vec3(11.3, 5.7, 3.1);
		amplitude *= 0.5;
	}
	return total / norm;
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 p = world_position * scale;
	float chips = fbm3(p, 5);
	float chip_mask = smoothstep(1.0 - chipping, 1.0 - chipping + 0.02, chips);
	float rust_mask = smoothstep(1.0 - chipping - rust_spread, 1.0 - chipping, chips) * (1.0 - chip_mask * 0.6);
	float streak_noise = fbm3(vec3(p.x * 2.0, p.y / streak_length, p.z * 2.0), 4);
	float streaks = smoothstep(0.55, 0.75, streak_noise) * streak_amount;
	float rust_tone = fbm3(p * 3.0 + 9.0, 3);
	vec3 rust = mix(rust_color.rgb, rust_dark.rgb, rust_tone);
	vec3 color = paint_color.rgb * (0.9 + 0.2 * fbm3(p * 0.5, 2));
	color = mix(color, rust, max(rust_mask, streaks * (1.0 - chip_mask)));
	color = mix(color, metal_color.rgb, chip_mask * (1.0 - rust_tone * 0.5));
	ALBEDO = color;
	METALLIC = chip_mask * 0.9;
	ROUGHNESS = mix(mix(0.55, 0.95, max(rust_mask, streaks)), 0.35, chip_mask);
}
