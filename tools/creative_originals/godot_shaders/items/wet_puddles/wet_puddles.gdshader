shader_type spatial;

uniform vec4 stone_color : source_color = vec4(0.5, 0.46, 0.42, 1.0);
uniform vec4 grout_color : source_color = vec4(0.22, 0.2, 0.18, 1.0);
uniform float stone_scale : hint_range(1.0, 40.0) = 7.0;
uniform float grout_width : hint_range(0.0, 0.3) = 0.08;
uniform float wetness : hint_range(0.0, 1.0) = 0.6;
uniform float puddle_amount : hint_range(0.0, 1.0) = 0.45;
uniform float puddle_scale : hint_range(0.1, 10.0) = 0.8;
uniform vec4 puddle_tint : source_color = vec4(0.16, 0.17, 0.19, 1.0);
uniform float ripple_strength : hint_range(0.0, 1.0) = 0.5;
uniform float ripple_density : hint_range(1.0, 30.0) = 6.0;
uniform float ripple_speed : hint_range(0.1, 4.0) = 1.2;

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

// x: distance to the nearest feature point, y: to the second nearest, z: random value of the nearest cell.
vec3 voronoi(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	float f1 = 8.0;
	float f2 = 8.0;
	float id = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 neighbor = vec2(float(x), float(y));
			vec2 feature = hash22(cell + neighbor);
			float d = length(neighbor + feature - f);
			if (d < f1) {
				f2 = f1;
				f1 = d;
				id = hash21(cell + neighbor + vec2(0.37, 0.71) * 101.0);
			} else if (d < f2) {
				f2 = d;
			}
		}
	}
	return vec3(f1, f2, id);
}

vec2 ripple_slope(vec2 p) {
	vec2 cell = floor(p);
	vec2 slope = vec2(0.0);
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 id = cell + vec2(float(x), float(y));
			vec2 center = id + hash22(id);
			float phase = fract(TIME * ripple_speed + hash21(id + 31.0));
			vec2 delta = p - center;
			float distance_to_center = length(delta);
			float ring = sin((distance_to_center - phase) * 40.0) * (1.0 - phase)
				* smoothstep(0.12, 0.0, abs(distance_to_center - phase));
			slope += ring * delta / max(distance_to_center, 1e-3);
		}
	}
	return slope;
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = world_position.xz;
	vec3 cells = voronoi(p * stone_scale);
	float grout = 1.0 - smoothstep(grout_width * 0.5, grout_width, cells.y - cells.x);
	vec3 stone = stone_color.rgb * mix(0.75, 1.15, cells.z);
	vec3 dry = mix(stone, grout_color.rgb, grout);
	float low = fbm(p * puddle_scale, 4) + grout * 0.15;
	float puddle = smoothstep(1.0 - puddle_amount, 1.0 - puddle_amount + 0.04, low);
	vec3 wet = dry * mix(1.0, 0.5, wetness);
	ALBEDO = mix(wet, puddle_tint.rgb, puddle);
	ROUGHNESS = mix(mix(0.85, 0.3, wetness), 0.03, puddle);
	SPECULAR = 0.5;
	vec2 slope = ripple_slope(p * ripple_density) * ripple_strength * puddle;
	NORMAL_MAP = normalize(vec3(-slope.x, -slope.y, 1.0)) * 0.5 + 0.5;
}
