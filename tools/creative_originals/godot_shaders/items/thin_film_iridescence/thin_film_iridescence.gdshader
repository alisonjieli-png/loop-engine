shader_type spatial;
render_mode cull_back, depth_draw_always;

uniform float film_index : hint_range(1.0, 2.5) = 1.33;
uniform float thickness_min_nm : hint_range(0.0, 1500.0) = 250.0;
uniform float thickness_max_nm : hint_range(0.0, 1500.0) = 750.0;
uniform float swirl_scale : hint_range(0.1, 10.0) = 2.0;
uniform float swirl_speed : hint_range(0.0, 2.0) = 0.15;
uniform float opacity : hint_range(0.0, 1.0) = 0.35;
uniform float roughness : hint_range(0.0, 1.0) = 0.05;
uniform vec4 base_color : source_color = vec4(0.02, 0.02, 0.03, 1.0);

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

vec3 film_color(float cos_incident, float thickness_nm) {
	float sin_incident = sqrt(max(1.0 - cos_incident * cos_incident, 0.0));
	float sin_refracted = sin_incident / film_index;
	float cos_refracted = sqrt(max(1.0 - sin_refracted * sin_refracted, 0.0));
	float path = 2.0 * film_index * thickness_nm * cos_refracted;
	vec3 wavelengths = vec3(650.0, 532.0, 450.0);
	return 0.5 + 0.5 * cos(TAU * path / wavelengths + PI);
}

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	float swirl = fbm3(object_position * swirl_scale + vec3(0.0, TIME * swirl_speed, TIME * swirl_speed * 0.5), 4);
	float gravity = clamp(0.5 - object_position.y, 0.0, 1.0);
	float thickness = mix(thickness_min_nm, thickness_max_nm, clamp(swirl * 0.8 + gravity * 0.4, 0.0, 1.0));
	float cos_incident = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec3 interference = film_color(cos_incident, thickness);
	ALBEDO = mix(base_color.rgb, interference, 0.85);
	METALLIC = 1.0;
	ROUGHNESS = roughness;
	float facing_alpha = mix(1.0, opacity, cos_incident);
	ALPHA = facing_alpha;
}
