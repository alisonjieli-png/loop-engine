shader_type spatial;
render_mode cull_disabled;

uniform vec4 warp_color : source_color = vec4(0.22, 0.32, 0.55, 1.0);
uniform vec4 weft_color : source_color = vec4(0.75, 0.72, 0.65, 1.0);
uniform float threads : hint_range(4.0, 400.0) = 60.0;
uniform bool twill = true;
uniform float thread_gap : hint_range(0.0, 0.4) = 0.12;
uniform float relief : hint_range(0.0, 1.0) = 0.6;
uniform float fuzz : hint_range(0.0, 1.0) = 0.25;
uniform float sheen : hint_range(0.0, 1.0) = 0.6;

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
	vec2 grid = UV * threads;
	vec2 cell = floor(grid);
	vec2 local = fract(grid);
	float shift = twill ? cell.y : 0.0;
	float over = mod(cell.x + shift, 2.0);
	float across = over > 0.5 ? local.y : local.x;
	float along = over > 0.5 ? local.x : local.y;
	float profile = sin(clamp((across - thread_gap * 0.5) / (1.0 - thread_gap), 0.0, 1.0) * PI);
	float gap = step(thread_gap * 0.5, across) * step(across, 1.0 - thread_gap * 0.5);
	float slope = cos(clamp((across - thread_gap * 0.5) / (1.0 - thread_gap), 0.0, 1.0) * PI) * relief;
	vec2 tilt = over > 0.5 ? vec2(0.0, slope) : vec2(slope, 0.0);
	float dip = sin(along * PI) * 0.3 * relief;
	NORMAL_MAP = normalize(vec3(-tilt, 1.0)) * 0.5 + 0.5;
	float fibre = value_noise(UV * threads * vec2(over > 0.5 ? 8.0 : 1.0, over > 0.5 ? 1.0 : 8.0)) * fuzz;
	vec3 thread = over > 0.5 ? weft_color.rgb : warp_color.rgb;
	vec3 color = thread * (0.6 + 0.4 * profile + dip * 0.2) * (1.0 - fuzz * 0.3 + fibre * 0.6);
	ALBEDO = mix(thread * 0.25, color, gap);
	ROUGHNESS = 0.85;
	RIM = sheen;
	RIM_TINT = 0.6;
}
