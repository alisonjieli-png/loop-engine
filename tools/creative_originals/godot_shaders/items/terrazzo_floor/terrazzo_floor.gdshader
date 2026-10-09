shader_type spatial;

uniform vec4 matrix_color : source_color = vec4(0.88, 0.86, 0.82, 1.0);
uniform vec4 chip_a : source_color = vec4(0.85, 0.45, 0.35, 1.0);
uniform vec4 chip_b : source_color = vec4(0.25, 0.42, 0.55, 1.0);
uniform vec4 chip_c : source_color = vec4(0.9, 0.78, 0.45, 1.0);
uniform vec4 chip_d : source_color = vec4(0.28, 0.28, 0.3, 1.0);
uniform float chip_scale : hint_range(1.0, 60.0) = 12.0;
uniform float chip_density : hint_range(0.0, 1.0) = 0.65;
uniform float chip_size : hint_range(0.1, 0.6) = 0.38;
uniform float edge_roughness : hint_range(0.0, 0.3) = 0.12;
uniform float speckle : hint_range(0.0, 1.0) = 0.35;
uniform float roughness : hint_range(0.0, 1.0) = 0.25;

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

vec4 nearest_chip(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	float best = 8.0;
	vec2 best_cell = cell;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 neighbor = vec2(float(x), float(y));
			vec2 id = cell + neighbor;
			float size = chip_size * mix(0.4, 1.3, hash21(id + 4.0)) * step(hash21(id + 8.0), chip_density);
			float d = length(neighbor + hash22(id) - f) / max(size, 1e-3);
			if (d < best) {
				best = d;
				best_cell = id;
			}
		}
	}
	return vec4(best, hash21(best_cell + 2.0), best_cell);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world_position.xz * chip_scale;
	vec4 chip = nearest_chip(p);
	float edge = (value_noise(p * 6.0) - 0.5) * edge_roughness * 4.0;
	float inside = 1.0 - step(1.0, chip.x + edge);
	float pick = chip.y;
	vec3 chip_color = pick < 0.25 ? chip_a.rgb : (pick < 0.5 ? chip_b.rgb : (pick < 0.75 ? chip_c.rgb : chip_d.rgb));
	chip_color *= 0.85 + 0.3 * hash21(chip.zw + 13.0);
	float fine = hash21(floor(p * 9.0));
	vec3 matrix = matrix_color.rgb * (1.0 - speckle * 0.25 * step(0.8, fine));
	ALBEDO = mix(matrix, chip_color, inside);
	ROUGHNESS = roughness;
	SPECULAR = 0.5;
}
