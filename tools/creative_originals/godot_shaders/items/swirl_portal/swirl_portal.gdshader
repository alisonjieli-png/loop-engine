shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque, shadows_disabled;

uniform vec4 outer_color : source_color = vec4(0.45, 0.15, 0.95, 1.0);
uniform vec4 inner_color : source_color = vec4(0.2, 0.9, 1.0, 1.0);
uniform vec4 core_color : source_color = vec4(0.02, 0.0, 0.05, 1.0);
uniform vec4 rim_color : source_color = vec4(1.0, 0.85, 1.0, 1.0);
uniform int arms : hint_range(1, 12) = 4;
uniform float twist : hint_range(0.0, 20.0) = 6.0;
uniform float spin_speed : hint_range(-10.0, 10.0) = 2.0;
uniform float core_radius : hint_range(0.0, 0.5) = 0.12;
uniform float rim_width : hint_range(0.0, 0.2) = 0.04;
uniform float sparkle_amount : hint_range(0.0, 1.0) = 0.5;
uniform float glow : hint_range(0.0, 4.0) = 1.4;

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
	vec2 p = (UV - 0.5) * 2.0;
	float radius = length(p);
	if (radius > 1.0) {
		discard;
	}
	float angle = atan(p.y, p.x);
	float spiral = angle * float(arms) + twist / (radius + 0.15) - TIME * spin_speed;
	float arms_mask = 0.5 + 0.5 * sin(spiral);
	float inward = fract(radius * 2.0 + TIME * 0.4);
	float sparkle = step(0.93, value_noise(vec2(angle * 8.0, radius * 14.0 + TIME * 3.0))) * sparkle_amount;
	vec3 color = mix(inner_color.rgb, outer_color.rgb, smoothstep(0.1, 0.9, radius));
	color *= 0.35 + 0.9 * arms_mask * (0.7 + 0.3 * inward);
	color += vec3(sparkle);
	color = mix(core_color.rgb, color, smoothstep(core_radius, core_radius + 0.12, radius));
	float rim = smoothstep(1.0 - rim_width * 2.0, 1.0 - rim_width, radius) * (1.0 - smoothstep(1.0 - rim_width * 0.5, 1.0, radius));
	color = mix(color, rim_color.rgb, rim);
	ALBEDO = color * glow;
}
