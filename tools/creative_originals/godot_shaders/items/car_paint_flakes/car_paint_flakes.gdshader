shader_type spatial;

uniform vec4 face_color : source_color = vec4(0.55, 0.04, 0.08, 1.0);
uniform vec4 edge_color : source_color = vec4(0.18, 0.02, 0.12, 1.0);
uniform float flip_power : hint_range(0.5, 6.0) = 1.6;
uniform float base_roughness : hint_range(0.0, 1.0) = 0.38;
uniform float flake_density : hint_range(0.0, 1.0) = 0.12;
uniform float flake_scale : hint_range(50.0, 2000.0) = 900.0;
uniform float flake_tilt : hint_range(0.0, 1.0) = 0.35;
uniform vec4 flake_color : source_color = vec4(1.0, 0.9, 0.85, 1.0);
uniform float clearcoat_amount : hint_range(0.0, 1.0) = 1.0;
uniform float clearcoat_gloss : hint_range(0.0, 1.0) = 0.95;

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

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec3 paint = mix(edge_color.rgb, face_color.rgb, pow(facing, 1.0 / flip_power));
	vec3 cell = floor(object_position * flake_scale);
	float present = step(1.0 - flake_density, hash31(cell));
	vec3 random_direction = vec3(hash31(cell + 11.0), hash31(cell + 23.0), hash31(cell + 37.0)) * 2.0 - 1.0;
	vec3 flake_normal = normalize(NORMAL + random_direction * flake_tilt);
	NORMAL = normalize(mix(NORMAL, flake_normal, present));
	ALBEDO = mix(paint, flake_color.rgb, present);
	METALLIC = mix(0.3, 0.85, present);
	ROUGHNESS = mix(base_roughness, 0.2, present);
	CLEARCOAT = clearcoat_amount;
	CLEARCOAT_ROUGHNESS = 1.0 - clearcoat_gloss;
}
