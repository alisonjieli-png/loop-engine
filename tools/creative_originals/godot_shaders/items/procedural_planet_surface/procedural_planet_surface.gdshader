shader_type spatial;

uniform vec4 deep_ocean : source_color = vec4(0.02, 0.08, 0.25, 1.0);
uniform vec4 shallow_ocean : source_color = vec4(0.08, 0.35, 0.55, 1.0);
uniform vec4 lowland : source_color = vec4(0.2, 0.42, 0.16, 1.0);
uniform vec4 desert : source_color = vec4(0.78, 0.66, 0.4, 1.0);
uniform vec4 highland : source_color = vec4(0.45, 0.38, 0.3, 1.0);
uniform vec4 ice : source_color = vec4(0.94, 0.96, 1.0, 1.0);
uniform float continent_scale : hint_range(0.5, 8.0) = 1.8;
uniform float sea_level : hint_range(0.0, 1.0) = 0.52;
uniform float mountain_strength : hint_range(0.0, 1.0) = 0.5;
uniform float ice_latitude : hint_range(0.0, 1.0) = 0.78;
uniform float desert_band : hint_range(0.0, 1.0) = 0.3;
uniform float spin_speed : hint_range(-1.0, 1.0) = 0.05;
uniform int seed : hint_range(0, 1000) = 7;

varying vec3 surface_direction;

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
	surface_direction = normalize(VERTEX);
}

void fragment() {
	float angle = TIME * spin_speed;
	vec3 d = surface_direction;
	d = vec3(d.x * cos(angle) - d.z * sin(angle), d.y, d.x * sin(angle) + d.z * cos(angle));
	vec3 p = d * continent_scale + vec3(float(seed) * 17.31);
	float continents = fbm3(p, 6);
	float ridges = 1.0 - abs(fbm3(p * 2.6 + 4.0, 4) * 2.0 - 1.0);
	float height = continents + (ridges * ridges - 0.4) * mountain_strength * smoothstep(sea_level, sea_level + 0.1, continents) * 0.25;
	float latitude = abs(d.y);
	float land = step(sea_level, height);
	vec3 ocean = mix(deep_ocean.rgb, shallow_ocean.rgb, smoothstep(sea_level - 0.12, sea_level, height));
	float above = clamp((height - sea_level) / (1.0 - sea_level), 0.0, 1.0);
	float dryness = (1.0 - smoothstep(0.0, desert_band, latitude)) * smoothstep(0.35, 0.65, fbm3(p * 1.7 + 9.0, 3));
	vec3 ground = mix(lowland.rgb, desert.rgb, dryness);
	ground = mix(ground, highland.rgb, smoothstep(0.2, 0.6, above));
	vec3 color = mix(ocean, ground, land);
	float ice_mask = smoothstep(ice_latitude - 0.04, ice_latitude + 0.04, latitude + (continents - 0.5) * 0.25);
	ice_mask = max(ice_mask, land * smoothstep(0.75, 0.9, above));
	color = mix(color, ice.rgb, ice_mask);
	ALBEDO = color;
	ROUGHNESS = mix(mix(0.25, 0.9, land), 0.6, ice_mask);
	SPECULAR = mix(0.6, 0.3, land);
}
