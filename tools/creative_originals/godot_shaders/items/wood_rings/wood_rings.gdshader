shader_type spatial;

uniform vec4 early_wood : source_color = vec4(0.78, 0.56, 0.34, 1.0);
uniform vec4 late_wood : source_color = vec4(0.45, 0.26, 0.13, 1.0);
uniform float ring_density : hint_range(1.0, 60.0) = 18.0;
uniform float ring_sharpness : hint_range(0.0, 1.0) = 0.7;
uniform float distortion : hint_range(0.0, 2.0) = 0.6;
uniform float grain_density : hint_range(10.0, 400.0) = 140.0;
uniform float grain_strength : hint_range(0.0, 1.0) = 0.25;
uniform float axis_tilt_degrees : hint_range(0.0, 45.0) = 4.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.65;

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

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	float tilt = radians(axis_tilt_degrees);
	vec3 p = object_position;
	p = vec3(p.x, p.y * cos(tilt) - p.z * sin(tilt), p.y * sin(tilt) + p.z * cos(tilt));
	float wobble = fbm3(p * vec3(1.5, 1.5, 0.35), 4) - 0.5;
	float radius = length(p.xy) + wobble * distortion * 0.15;
	float rings = fract(radius * ring_density);
	float late = smoothstep(mix(0.4, 0.75, ring_sharpness), 1.0, rings) + (1.0 - smoothstep(0.0, 0.08, rings)) * 0.5;
	float ring_index = floor(radius * ring_density);
	float variation = hash31(vec3(ring_index, 3.0, 7.0)) * 0.15;
	float grain = value_noise3(vec3(p.x * grain_density, p.y * grain_density, p.z * 4.0));
	vec3 color = mix(early_wood.rgb, late_wood.rgb, clamp(late, 0.0, 1.0));
	color *= 1.0 - variation + (grain - 0.5) * grain_strength;
	ALBEDO = color;
	ROUGHNESS = roughness - late * 0.1;
}
