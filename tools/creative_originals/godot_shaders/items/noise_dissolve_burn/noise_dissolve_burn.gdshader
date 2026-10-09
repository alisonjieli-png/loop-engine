shader_type spatial;
render_mode cull_disabled;

uniform vec4 albedo : source_color = vec4(0.82, 0.78, 0.72, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.6;
uniform float dissolve : hint_range(0.0, 1.0) = 0.45;
uniform float noise_scale : hint_range(0.5, 20.0) = 4.0;
uniform float edge_width : hint_range(0.0, 0.2) = 0.04;
uniform float char_width : hint_range(0.0, 0.3) = 0.08;
uniform vec4 edge_color : source_color = vec4(1.0, 0.42, 0.06, 1.0);
uniform vec4 ember_color : source_color = vec4(1.0, 0.9, 0.55, 1.0);
uniform float edge_emission : hint_range(0.0, 12.0) = 5.0;
uniform bool loop_animation = false;
uniform float loop_speed : hint_range(0.0, 2.0) = 0.2;

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
	float amount = loop_animation ? 0.5 - 0.5 * cos(TIME * loop_speed * TAU) : dissolve;
	float n = fbm3(object_position * noise_scale, 4);
	float cut = mix(-0.05, 1.05, amount);
	float distance_to_cut = n - cut;
	if (distance_to_cut < 0.0) {
		discard;
	}
	float present = step(0.001, amount);
	float edge = (1.0 - smoothstep(0.0, edge_width, distance_to_cut)) * present;
	float charred = (1.0 - smoothstep(edge_width, edge_width + char_width, distance_to_cut)) * present;
	ALBEDO = mix(albedo.rgb, albedo.rgb * 0.12, charred);
	ROUGHNESS = mix(roughness, 1.0, charred);
	EMISSION = mix(edge_color.rgb, ember_color.rgb, edge * edge) * edge * edge_emission;
}
