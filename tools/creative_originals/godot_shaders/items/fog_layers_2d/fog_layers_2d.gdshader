shader_type canvas_item;

uniform vec4 fog_color : source_color = vec4(0.85, 0.88, 0.92, 1.0);
uniform float density : hint_range(0.0, 2.0) = 0.9;
uniform float ground_line : hint_range(0.0, 1.0) = 0.8;
uniform float fog_height : hint_range(0.05, 1.0) = 0.45;
uniform float drift_speed : hint_range(-0.5, 0.5) = 0.04;
uniform float scale : hint_range(0.5, 12.0) = 3.0;
uniform int layers : hint_range(1, 6) = 3;

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
	float total = 0.0;
	for (int i = 0; i < layers; i++) {
		float fi = float(i);
		float layer_scale = scale * (1.0 + fi * 0.6);
		vec2 p = vec2(UV.x * layer_scale * 1.5 + TIME * drift_speed * (1.0 + fi * 0.7) * layer_scale + fi * 7.3,
					  UV.y * layer_scale * 0.6);
		float n = fbm(p, 4);
		float base = ground_line - fi * 0.08;
		float height_mask = smoothstep(base - fog_height, base, UV.y);
		total += smoothstep(0.35, 0.75, n) * height_mask * (1.0 - fi * 0.2);
	}
	float alpha = clamp(total * density / float(layers) * 1.5, 0.0, 1.0);
	COLOR = vec4(fog_color.rgb, alpha * fog_color.a);
}
