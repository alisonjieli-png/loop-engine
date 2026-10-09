shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float strength : hint_range(0.0, 0.1) = 0.018;
uniform float noise_scale : hint_range(1.0, 40.0) = 9.0;
uniform float rise_speed : hint_range(0.0, 5.0) = 1.4;
uniform float edge_softness : hint_range(0.01, 0.5) = 0.25;
uniform float top_fade : hint_range(0.0, 1.0) = 0.6;
uniform float distance_falloff : hint_range(0.0, 1.0) = 0.15;
uniform float tint_amount : hint_range(0.0, 0.3) = 0.04;

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
	vec2 p = UV * noise_scale;
	float t = TIME * rise_speed;
	vec2 flow = vec2(value_noise(p + vec2(0.0, t)), value_noise(p * 1.7 + vec2(5.3, t * 1.3))) - 0.5;
	float mask = smoothstep(0.0, edge_softness, UV.x) * smoothstep(1.0, 1.0 - edge_softness, UV.x);
	mask *= smoothstep(1.0, 1.0 - edge_softness, UV.y) * mix(1.0, UV.y, top_fade);
	mask *= 1.0 / (1.0 + length(VERTEX) * distance_falloff);
	vec2 offset = flow * strength * mask;
	vec3 behind = textureLod(screen_texture, SCREEN_UV + offset, 0.0).rgb;
	ALBEDO = behind * (1.0 + tint_amount * mask * vec3(1.0, 0.6, 0.3));
}
