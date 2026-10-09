shader_type spatial;
render_mode cull_disabled, depth_draw_always;

uniform vec4 glass_a : source_color = vec4(0.75, 0.12, 0.15, 1.0);
uniform vec4 glass_b : source_color = vec4(0.12, 0.3, 0.75, 1.0);
uniform vec4 glass_c : source_color = vec4(0.95, 0.75, 0.15, 1.0);
uniform vec4 glass_d : source_color = vec4(0.15, 0.55, 0.25, 1.0);
uniform vec4 lead_color : source_color = vec4(0.06, 0.06, 0.07, 1.0);
uniform float cell_scale : hint_range(1.0, 30.0) = 6.0;
uniform float lead_width : hint_range(0.0, 0.3) = 0.07;
uniform float backlight : hint_range(0.0, 4.0) = 1.6;
uniform float mottling : hint_range(0.0, 1.0) = 0.35;
uniform float glass_opacity : hint_range(0.0, 1.0) = 0.85;

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

// x: distance to the nearest feature point, y: to the second nearest, z: random value of the nearest cell.
vec3 voronoi(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	float f1 = 8.0;
	float f2 = 8.0;
	float id = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 neighbor = vec2(float(x), float(y));
			vec2 feature = hash22(cell + neighbor);
			float d = length(neighbor + feature - f);
			if (d < f1) {
				f2 = f1;
				f1 = d;
				id = hash21(cell + neighbor + vec2(0.37, 0.71) * 101.0);
			} else if (d < f2) {
				f2 = d;
			}
		}
	}
	return vec3(f1, f2, id);
}

void fragment() {
	vec2 p = UV * cell_scale;
	vec3 cells = voronoi(p);
	float lead = 1.0 - smoothstep(lead_width * 0.5, lead_width, cells.y - cells.x);
	float pick = cells.z;
	vec3 glass = pick < 0.25 ? glass_a.rgb : (pick < 0.5 ? glass_b.rgb : (pick < 0.75 ? glass_c.rgb : glass_d.rgb));
	float mottle = fbm(p * 3.0, 3);
	glass *= 1.0 - mottling * 0.5 + mottle * mottling;
	float border = smoothstep(0.02, 0.0, min(min(UV.x, UV.y), min(1.0 - UV.x, 1.0 - UV.y)));
	lead = max(lead, border);
	ALBEDO = mix(glass * 0.3, lead_color.rgb, lead);
	EMISSION = glass * backlight * (1.0 - lead);
	ROUGHNESS = mix(0.15, 0.7, lead);
	ALPHA = mix(glass_opacity, 1.0, lead);
}
