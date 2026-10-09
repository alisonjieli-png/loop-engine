shader_type spatial;
render_mode cull_disabled;

uniform vec4 root_color : source_color = vec4(0.12, 0.06, 0.03, 1.0);
uniform vec4 tip_color : source_color = vec4(0.45, 0.25, 0.12, 1.0);
uniform vec4 secondary_tint : source_color = vec4(0.85, 0.55, 0.3, 1.0);
uniform float primary_shift : hint_range(-1.0, 1.0) = 0.1;
uniform float secondary_shift : hint_range(-1.0, 1.0) = -0.15;
uniform float primary_exponent : hint_range(4.0, 512.0) = 160.0;
uniform float secondary_exponent : hint_range(4.0, 512.0) = 40.0;
uniform float strand_noise : hint_range(0.0, 1.0) = 0.4;
uniform float strand_count : hint_range(10.0, 2000.0) = 400.0;
uniform float highlight_strength : hint_range(0.0, 2.0) = 0.6;

varying vec3 strand_tangent;
varying float strand_jitter;

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

void fragment() {
	strand_tangent = normalize(-BINORMAL);
	strand_jitter = value_noise(vec2(UV.x * strand_count, 0.5)) - 0.5;
	ALBEDO = mix(root_color.rgb, tip_color.rgb, clamp(UV.y, 0.0, 1.0)) * (1.0 + strand_jitter * strand_noise * 0.5);
}

float strand_specular(vec3 tangent, vec3 normal, float shift, vec3 halfway, float exponent) {
	vec3 shifted = normalize(tangent + normal * shift);
	float t_dot_h = dot(shifted, halfway);
	float sine = sqrt(max(1.0 - t_dot_h * t_dot_h, 0.0));
	return pow(sine, exponent) * smoothstep(-1.0, 0.0, t_dot_h);
}

void light() {
	vec3 halfway = normalize(LIGHT + VIEW);
	float jitter = strand_jitter * strand_noise;
	float primary = strand_specular(strand_tangent, NORMAL, primary_shift + jitter, halfway, primary_exponent);
	float secondary = strand_specular(strand_tangent, NORMAL, secondary_shift + jitter, halfway, secondary_exponent);
	float n_dot_l = clamp(dot(NORMAL, LIGHT), 0.0, 1.0);
	DIFFUSE_LIGHT += clamp(mix(0.25, 1.0, n_dot_l), 0.0, 1.0) * ATTENUATION * LIGHT_COLOR / PI;
	vec3 specular = vec3(primary) + secondary * secondary_tint.rgb * ALBEDO * 4.0;
	SPECULAR_LIGHT += specular * highlight_strength * n_dot_l * ATTENUATION * LIGHT_COLOR / PI;
}
