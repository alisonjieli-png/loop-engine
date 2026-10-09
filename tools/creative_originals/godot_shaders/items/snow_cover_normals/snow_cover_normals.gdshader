shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.36, 0.3, 0.26, 1.0);
uniform float base_roughness : hint_range(0.0, 1.0) = 0.85;
uniform float base_pattern_scale : hint_range(0.5, 40.0) = 12.0;
uniform vec4 snow_color : source_color = vec4(0.95, 0.97, 1.0, 1.0);
uniform float snow_amount : hint_range(0.0, 1.0) = 0.55;
uniform float snow_sharpness : hint_range(0.01, 0.5) = 0.06;
uniform float noise_scale : hint_range(0.5, 30.0) = 5.0;
uniform float noise_strength : hint_range(0.0, 1.0) = 0.35;
uniform float snow_lift : hint_range(0.0, 0.1) = 0.015;
uniform float sparkle_density : hint_range(0.0, 1.0) = 0.25;

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

float coverage(vec3 world_normal, vec3 position) {
	float threshold = 1.0 - snow_amount * 2.0;
	float n = fbm3(position * noise_scale, 3) - 0.5;
	return smoothstep(threshold - snow_sharpness, threshold + snow_sharpness, world_normal.y + n * noise_strength);
}

void vertex() {
	vec3 world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX += NORMAL * snow_lift * coverage(world_normal, world_position);
}

void fragment() {
	vec3 world_normal = normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	float cover = coverage(world_normal, world_position);
	float grain = fbm3(world_position * base_pattern_scale, 3);
	vec3 ground = base_color.rgb * mix(0.6, 1.25, grain);
	ALBEDO = mix(ground, snow_color.rgb, cover);
	ROUGHNESS = mix(base_roughness, 0.7, cover);
	vec3 cell = floor(world_position * 90.0);
	float glint = step(1.0 - sparkle_density * 0.03, hash31(cell));
	float aligned = pow(clamp(dot(reflect(-VIEW, NORMAL), normalize(vec3(0.3, 0.8, 0.5))), 0.0, 1.0), 2.0);
	EMISSION = vec3(glint * cover * (0.3 + aligned) * 1.5);
}
