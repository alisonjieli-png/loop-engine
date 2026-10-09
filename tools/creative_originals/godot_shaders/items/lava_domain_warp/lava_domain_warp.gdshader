shader_type spatial;

uniform vec4 crust_color : source_color = vec4(0.07, 0.05, 0.05, 1.0);
uniform vec4 lava_dark : source_color = vec4(0.62, 0.07, 0.02, 1.0);
uniform vec4 lava_bright : source_color = vec4(1.0, 0.66, 0.16, 1.0);
uniform float scale : hint_range(0.5, 20.0) = 3.0;
uniform float flow_speed : hint_range(0.0, 2.0) = 0.12;
uniform float flow_angle_degrees : hint_range(0.0, 360.0) = 20.0;
uniform float warp_strength : hint_range(0.0, 4.0) = 1.8;
uniform float crust_amount : hint_range(0.0, 1.0) = 0.5;
uniform float crust_edge : hint_range(0.01, 0.3) = 0.06;
uniform float emission_strength : hint_range(0.0, 10.0) = 3.0;

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

float lava_field(vec2 p, float t) {
	vec2 q = vec2(fbm(p + vec2(0.0, 0.0), 4), fbm(p + vec2(5.2, 1.3), 4));
	vec2 r = vec2(fbm(p + warp_strength * q + vec2(1.7, 9.2) + 0.15 * t, 4),
				  fbm(p + warp_strength * q + vec2(8.3, 2.8) + 0.126 * t, 4));
	return fbm(p + warp_strength * r, 4);
}

void fragment() {
	float angle = radians(flow_angle_degrees);
	vec2 flow = vec2(cos(angle), sin(angle)) * TIME * flow_speed;
	float heat = lava_field(UV * scale - flow, TIME);
	float crust = smoothstep(crust_amount - crust_edge, crust_amount + crust_edge, 1.0 - heat);
	float glow = smoothstep(0.35, 0.85, heat);
	vec3 molten = mix(lava_dark.rgb, lava_bright.rgb, glow);
	ALBEDO = mix(molten * 0.4, crust_color.rgb, crust);
	ROUGHNESS = mix(0.45, 0.95, crust);
	EMISSION = molten * (1.0 - crust) * emission_strength * (0.4 + glow);
}
