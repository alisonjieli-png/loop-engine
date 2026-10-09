shader_type spatial;

uniform vec4 metal_color : source_color = vec4(0.82, 0.83, 0.85, 1.0);
uniform float roughness_along : hint_range(0.02, 1.0) = 0.08;
uniform float roughness_across : hint_range(0.02, 1.0) = 0.45;
uniform bool circular = false;
uniform float circle_center_u : hint_range(0.0, 1.0) = 0.5;
uniform float circle_center_v : hint_range(0.0, 1.0) = 0.5;
uniform float streak_density : hint_range(10.0, 2000.0) = 600.0;
uniform float streak_strength : hint_range(0.0, 1.0) = 0.25;
uniform float diffuse_amount : hint_range(0.0, 1.0) = 0.15;
uniform float specular_strength : hint_range(0.0, 2.0) = 0.2;

varying vec3 brush_direction;
varying float streak;

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
	vec2 to_center = UV - vec2(circle_center_u, circle_center_v);
	vec3 direction = TANGENT;
	float across = UV.y;
	if (circular) {
		vec2 around = normalize(vec2(-to_center.y, to_center.x) + vec2(1e-5));
		direction = around.x * TANGENT + around.y * BINORMAL;
		across = length(to_center);
	}
	brush_direction = normalize(direction - NORMAL * dot(direction, NORMAL));
	streak = value_noise(vec2(across * streak_density, 0.5)) * 0.6 + value_noise(vec2(across * streak_density * 3.1, 7.0)) * 0.4;
	ALBEDO = metal_color.rgb * (1.0 - streak_strength * 0.5 + streak * streak_strength);
}

void light() {
	vec3 n = NORMAL;
	float n_dot_l = dot(n, LIGHT);
	float n_dot_v = dot(n, VIEW);
	if (n_dot_l > 0.0 && n_dot_v > 0.0) {
		vec3 t = normalize(brush_direction);
		vec3 b = normalize(cross(n, t));
		vec3 h = normalize(LIGHT + VIEW);
		float ht = dot(h, t) / roughness_along;
		float hb = dot(h, b) / roughness_across;
		float hn = max(dot(h, n), 1e-4);
		float ward = exp(-(ht * ht + hb * hb) / (hn * hn))
			/ (4.0 * PI * roughness_along * roughness_across * sqrt(n_dot_l * n_dot_v));
		SPECULAR_LIGHT += ALBEDO * ward * specular_strength * n_dot_l * ATTENUATION * LIGHT_COLOR / PI;
		DIFFUSE_LIGHT += diffuse_amount * n_dot_l * ATTENUATION * LIGHT_COLOR / PI;
	}
}
