shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 core_color : source_color = vec4(1.0, 0.95, 0.6, 1.0);
uniform vec4 mid_color : source_color = vec4(1.0, 0.5, 0.08, 1.0);
uniform vec4 tip_color : source_color = vec4(0.6, 0.05, 0.02, 1.0);
uniform float rise_speed : hint_range(0.0, 5.0) = 1.6;
uniform float noise_scale : hint_range(1.0, 20.0) = 5.0;
uniform float distortion : hint_range(0.0, 1.0) = 0.35;
uniform float flame_width : hint_range(0.1, 1.0) = 0.55;
uniform float flame_height : hint_range(0.2, 1.5) = 0.9;
uniform float intensity : hint_range(0.0, 4.0) = 1.6;

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
	// Spherical billboard: keep the node's position and scale, take the rotation from the camera.
	vec3 scale = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
	mat4 facing = mat4(INV_VIEW_MATRIX[0] * scale.x, INV_VIEW_MATRIX[1] * scale.y, INV_VIEW_MATRIX[2] * scale.z,
					   MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = VIEW_MATRIX * facing;
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 p = vec2(UV.x - 0.5, 1.0 - UV.y);
	float t = TIME * rise_speed;
	vec2 warp = vec2(value_noise(p * noise_scale + vec2(0.0, -t)), value_noise(p * noise_scale + vec2(4.7, -t * 1.3)));
	vec2 q = p + (warp - 0.5) * distortion * p.y;
	float n = fbm(q * noise_scale * vec2(1.0, 0.6) + vec2(0.0, -t * 1.6), 4);
	float width = flame_width * 0.5 * (1.0 - smoothstep(0.0, flame_height, q.y)) * (0.6 + 0.4 * smoothstep(0.0, 0.15, q.y));
	float shape = 1.0 - smoothstep(width * 0.6, width, abs(q.x));
	float heat = clamp(shape * (n * 1.3 - q.y / flame_height * 0.8 + 0.25), 0.0, 1.0);
	vec3 color = mix(tip_color.rgb, mid_color.rgb, smoothstep(0.1, 0.5, heat));
	color = mix(color, core_color.rgb, smoothstep(0.55, 0.9, heat));
	ALBEDO = color * smoothstep(0.05, 0.3, heat) * intensity;
}
