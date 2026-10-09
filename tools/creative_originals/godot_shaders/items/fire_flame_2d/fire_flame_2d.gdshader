shader_type canvas_item;

uniform vec4 core_color : source_color = vec4(1.0, 0.97, 0.75, 1.0);
uniform vec4 inner_color : source_color = vec4(1.0, 0.75, 0.2, 1.0);
uniform vec4 outer_color : source_color = vec4(0.95, 0.3, 0.05, 1.0);
uniform vec4 smoke_color : source_color = vec4(0.3, 0.05, 0.02, 1.0);
uniform float rise_speed : hint_range(0.0, 5.0) = 1.8;
uniform float turbulence : hint_range(0.0, 1.0) = 0.4;
uniform float base_width : hint_range(0.1, 1.0) = 0.5;
uniform float height : hint_range(0.2, 1.2) = 0.85;
uniform float noise_scale : hint_range(1.0, 12.0) = 4.0;

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
	vec2 p = vec2(UV.x - 0.5, 1.0 - UV.y);
	float t = TIME * rise_speed;
	float wobble = (value_noise(vec2(p.y * 4.0 - t, 1.3)) - 0.5) * turbulence * p.y;
	p.x += wobble;
	float n = fbm(vec2(p.x * noise_scale, p.y * noise_scale * 0.7 - t * 1.5), 5);
	float width = base_width * 0.5 * (1.0 - smoothstep(0.0, height, p.y)) * smoothstep(-0.05, 0.12, p.y);
	float shape = 1.0 - smoothstep(width * 0.4, width, abs(p.x));
	float heat = shape * (n * 1.4 - p.y / height * 0.9 + 0.35);
	vec3 color = mix(smoke_color.rgb, outer_color.rgb, smoothstep(0.05, 0.25, heat));
	color = mix(color, inner_color.rgb, smoothstep(0.3, 0.55, heat));
	color = mix(color, core_color.rgb, smoothstep(0.6, 0.85, heat));
	COLOR = vec4(color, smoothstep(0.02, 0.18, heat));
}
