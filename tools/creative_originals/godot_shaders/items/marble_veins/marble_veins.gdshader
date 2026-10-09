shader_type spatial;

uniform vec4 body_color : source_color = vec4(0.92, 0.91, 0.88, 1.0);
uniform vec4 cloud_color : source_color = vec4(0.82, 0.8, 0.78, 1.0);
uniform vec4 vein_color : source_color = vec4(0.25, 0.27, 0.3, 1.0);
uniform float scale : hint_range(0.2, 10.0) = 1.6;
uniform float vein_frequency : hint_range(0.5, 20.0) = 3.5;
uniform float turbulence : hint_range(0.0, 10.0) = 4.5;
uniform float vein_sharpness : hint_range(1.0, 40.0) = 14.0;
uniform float fine_veins : hint_range(0.0, 1.0) = 0.4;
uniform float roughness : hint_range(0.0, 1.0) = 0.12;

varying vec3 object_position;

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

float turbulent(vec3 p) {
	float total = 0.0;
	float amplitude = 1.0;
	for (int i = 0; i < 5; i++) {
		total += abs(value_noise3(p) * 2.0 - 1.0) * amplitude;
		p *= 2.0;
		amplitude *= 0.5;
	}
	return total;
}

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	vec3 p = object_position * scale;
	float main_vein = 1.0 - abs(sin((p.x + p.y * 0.4) * vein_frequency + turbulent(p) * turbulence));
	main_vein = pow(main_vein, vein_sharpness);
	float fine = 1.0 - abs(sin((p.z - p.x * 0.6) * vein_frequency * 2.3 + turbulent(p * 1.7 + 5.0) * turbulence));
	fine = pow(fine, vein_sharpness * 2.0) * fine_veins;
	float clouds = fbm3(p * 0.8, 4);
	vec3 color = mix(body_color.rgb, cloud_color.rgb, smoothstep(0.35, 0.7, clouds));
	color = mix(color, vein_color.rgb, clamp(main_vein + fine, 0.0, 1.0));
	ALBEDO = color;
	ROUGHNESS = roughness + main_vein * 0.15;
	SPECULAR = 0.6;
}
