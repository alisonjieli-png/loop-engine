shader_type canvas_item;

uniform vec4 space_color : source_color = vec4(0.01, 0.01, 0.04, 1.0);
uniform vec4 nebula_tint : source_color = vec4(0.12, 0.05, 0.2, 1.0);
uniform float density : hint_range(0.0, 1.0) = 0.45;
uniform float scroll_speed : hint_range(-2.0, 2.0) = 0.05;
uniform float scroll_angle_degrees : hint_range(0.0, 360.0) = 200.0;
uniform float twinkle_speed : hint_range(0.0, 10.0) = 3.0;
uniform float star_scale : hint_range(10.0, 200.0) = 60.0;
uniform float brightness : hint_range(0.0, 3.0) = 1.3;

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

vec3 star_layer(vec2 uv, float scale, float speed, float size, float salt) {
	float angle = radians(scroll_angle_degrees);
	vec2 p = uv * scale + vec2(cos(angle), sin(angle)) * TIME * scroll_speed * scale * speed;
	vec2 cell = floor(p);
	vec2 local = fract(p) - 0.5;
	float chance = hash21(cell + salt);
	if (chance > density * 0.35) {
		return vec3(0.0);
	}
	vec2 offset = hash22(cell + salt * 2.0) - 0.5;
	float distance_to_star = length(local - offset * 0.7);
	float core = smoothstep(size, 0.0, distance_to_star);
	float twinkle = 0.65 + 0.35 * sin(TIME * twinkle_speed * (0.5 + chance * 3.0) + chance * 60.0);
	float temperature = hash21(cell + salt * 3.0);
	vec3 color = mix(vec3(0.7, 0.8, 1.0), vec3(1.0, 0.85, 0.65), temperature);
	return color * core * twinkle;
}

void fragment() {
	vec2 uv = UV;
	vec3 color = mix(space_color.rgb, nebula_tint.rgb, fbm(UV * 3.0 + TIME * 0.01, 4) * 0.8);
	color += star_layer(uv, star_scale * 0.5, 0.3, 0.12, 1.0);
	color += star_layer(uv, star_scale, 0.6, 0.1, 17.0) * 0.8;
	color += star_layer(uv, star_scale * 2.0, 1.0, 0.09, 43.0) * 0.6;
	COLOR = vec4(color * brightness, 1.0);
}
