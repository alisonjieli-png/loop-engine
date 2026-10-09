shader_type spatial;

uniform float height_scale : hint_range(0.0, 5.0) = 1.4;
uniform float frequency : hint_range(0.05, 4.0) = 0.45;
uniform int noise_octaves : hint_range(1, 8) = 5;
uniform float sea_level : hint_range(0.0, 1.0) = 0.38;
uniform vec4 water_color : source_color = vec4(0.12, 0.35, 0.55, 1.0);
uniform vec4 sand_color : source_color = vec4(0.82, 0.74, 0.52, 1.0);
uniform vec4 grass_color : source_color = vec4(0.25, 0.48, 0.18, 1.0);
uniform vec4 rock_color : source_color = vec4(0.42, 0.38, 0.34, 1.0);
uniform vec4 snow_color : source_color = vec4(0.94, 0.96, 1.0, 1.0);
uniform float sand_band : hint_range(0.0, 0.2) = 0.035;
uniform float rock_slope : hint_range(0.0, 1.0) = 0.78;
uniform float snow_line : hint_range(0.0, 1.0) = 0.72;

varying float terrain_height;
varying vec3 world_normal;

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

float height_at(vec2 p) {
	return fbm(p * frequency, noise_octaves);
}

void vertex() {
	vec2 p = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
	float e = 0.05;
	float h = height_at(p);
	float hx = height_at(p + vec2(e, 0.0));
	float hz = height_at(p + vec2(0.0, e));
	terrain_height = h;
	float land = max(h, sea_level);
	VERTEX.y += (land - sea_level) * height_scale;
	vec3 normal = h > sea_level ? normalize(vec3((h - hx) * height_scale, e, (h - hz) * height_scale))
								: vec3(0.0, 1.0, 0.0);
	world_normal = normal;
	NORMAL = normalize(transpose(mat3(MODEL_MATRIX)) * normal);
}

void fragment() {
	float h = terrain_height;
	float flatness = world_normal.y;
	vec3 color = grass_color.rgb;
	color = mix(sand_color.rgb, color, smoothstep(sea_level + sand_band * 0.5, sea_level + sand_band, h));
	color = mix(rock_color.rgb, color, smoothstep(rock_slope - 0.05, rock_slope + 0.05, flatness));
	float snow = smoothstep(snow_line - 0.02, snow_line + 0.02, h + (flatness - 0.8) * 0.15);
	color = mix(color, snow_color.rgb, snow);
	float water = step(h, sea_level);
	ALBEDO = mix(color, water_color.rgb, water);
	ROUGHNESS = mix(0.9, 0.15, water);
}
