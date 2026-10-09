shader_type spatial;

uniform vec4 low_color : source_color = vec4(0.18, 0.42, 0.3, 1.0);
uniform vec4 high_color : source_color = vec4(0.85, 0.82, 0.55, 1.0);
uniform float gradient_bottom : hint_range(-5.0, 5.0) = -0.6;
uniform float gradient_top : hint_range(-5.0, 5.0) = 0.6;
uniform float facet_variation : hint_range(0.0, 0.5) = 0.12;
uniform float jitter : hint_range(0.0, 0.3) = 0.06;
uniform float roughness : hint_range(0.0, 1.0) = 0.9;

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

void vertex() {
	vec3 cell = floor(VERTEX * 50.0 + 0.5);
	vec3 offset = vec3(hash31(cell), hash31(cell + 13.0), hash31(cell + 29.0)) - 0.5;
	VERTEX += offset * jitter;
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 face_normal = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));
	NORMAL = face_normal;
	vec3 world_face = (INV_VIEW_MATRIX * vec4(face_normal, 0.0)).xyz;
	float facet = hash31(floor(world_face * 40.0)) - 0.5;
	float height = smoothstep(gradient_bottom, gradient_top, world_position.y);
	ALBEDO = mix(low_color.rgb, high_color.rgb, height) * (1.0 + facet * facet_variation * 2.0);
	ROUGHNESS = roughness;
}
