shader_type spatial;

uniform vec4 core_color : source_color = vec4(0.35, 0.03, 0.12, 1.0);
uniform vec4 sheen_color : source_color = vec4(1.0, 0.55, 0.7, 1.0);
uniform float sheen_power : hint_range(0.5, 8.0) = 2.2;
uniform float sheen_strength : hint_range(0.0, 3.0) = 1.2;
uniform float back_scatter : hint_range(0.0, 2.0) = 0.5;
uniform float diffuse_softness : hint_range(0.0, 1.0) = 0.5;
uniform float fiber_noise : hint_range(0.0, 1.0) = 0.15;

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
	float fibers = value_noise(UV * 300.0) * fiber_noise;
	ALBEDO = core_color.rgb * (1.0 - fiber_noise * 0.5 + fibers);
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float n_dot_v = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float soft = clamp((n_dot_l + diffuse_softness) / (1.0 + diffuse_softness), 0.0, 1.0);
	DIFFUSE_LIGHT += soft * ATTENUATION * LIGHT_COLOR / PI;
	float grazing = pow(1.0 - n_dot_v, sheen_power);
	float lit = clamp(n_dot_l * 0.5 + 0.5, 0.0, 1.0);
	float scatter = pow(clamp(dot(VIEW, -LIGHT), 0.0, 1.0), 3.0) * back_scatter;
	SPECULAR_LIGHT += sheen_color.rgb * (grazing * lit * sheen_strength + scatter * grazing) * ATTENUATION * LIGHT_COLOR / PI;
}
