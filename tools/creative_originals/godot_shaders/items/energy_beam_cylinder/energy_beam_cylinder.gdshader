shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 core_color : source_color = vec4(1.0, 0.95, 0.85, 1.0);
uniform vec4 beam_color : source_color = vec4(1.0, 0.3, 0.15, 1.0);
uniform float intensity : hint_range(0.0, 6.0) = 2.0;
uniform float core_sharpness : hint_range(0.5, 10.0) = 3.0;
uniform float scroll_speed : hint_range(-10.0, 10.0) = 3.0;
uniform float noise_scale : hint_range(1.0, 40.0) = 10.0;
uniform float pulse_spacing : hint_range(0.05, 1.0) = 0.25;
uniform float pulse_strength : hint_range(0.0, 2.0) = 0.6;
uniform float end_fade : hint_range(0.0, 0.5) = 0.08;
uniform float jitter : hint_range(0.0, 0.2) = 0.03;

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

void vertex() {
	float wobble = value_noise(vec2(UV.y * 12.0, TIME * 20.0)) - 0.5;
	VERTEX.xz *= 1.0 + wobble * jitter * 10.0;
}

void fragment() {
	float facing = abs(dot(NORMAL, VIEW));
	float core = pow(facing, core_sharpness);
	float along = UV.y;
	float flow = value_noise(vec2(UV.x * 6.0, along * noise_scale - TIME * scroll_speed));
	float pulse = smoothstep(0.7, 1.0, fract(along / pulse_spacing - TIME * scroll_speed * 0.25));
	float ends = smoothstep(0.0, end_fade, along) * smoothstep(1.0, 1.0 - end_fade, along);
	vec3 color = mix(beam_color.rgb, core_color.rgb, core) * (0.5 + flow + pulse * pulse_strength);
	ALBEDO = color * intensity * facing * ends;
}
