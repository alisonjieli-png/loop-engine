shader_type spatial;
render_mode unshaded, cull_back, depth_draw_never, shadows_disabled;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 shallow_color : source_color = vec4(0.38, 0.86, 0.85, 0.7);
uniform vec4 deep_color : source_color = vec4(0.05, 0.32, 0.55, 0.95);
uniform float depth_range : hint_range(0.05, 5.0) = 1.0;
uniform int color_steps : hint_range(1, 8) = 3;
uniform vec4 foam_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float foam_distance : hint_range(0.0, 1.0) = 0.18;
uniform float foam_noise_scale : hint_range(1.0, 40.0) = 9.0;
uniform float foam_speed : hint_range(0.0, 2.0) = 0.25;
uniform float ripple_amount : hint_range(0.0, 1.0) = 0.35;
uniform float ripple_scale : hint_range(0.5, 20.0) = 3.0;

// Linear view depth of the opaque scene at a screen position (metres from the camera plane).
float scene_view_depth(vec2 screen_uv, mat4 inv_projection) {
	float raw = texture(depth_texture, screen_uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw * 2.0 - 1.0);
#else
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return -view.z / view.w;
}

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
	float scene_depth = scene_view_depth(SCREEN_UV, INV_PROJECTION_MATRIX);
	float water_depth = max(scene_depth + VERTEX.z, 0.0);
	float t = clamp(water_depth / depth_range, 0.0, 1.0);
	float steps = float(color_steps);
	t = min(floor(t * steps) / max(steps - 1.0, 1.0), 1.0);
	vec4 water = mix(shallow_color, deep_color, t);
	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float drift = value_noise(world.xz * foam_noise_scale + vec2(TIME * foam_speed, TIME * foam_speed * 0.7));
	float foam = step(water_depth, foam_distance * (0.45 + 1.1 * drift));
	float ripple_field = fbm(world.xz * ripple_scale + vec2(TIME * 0.1, -TIME * 0.07), 3);
	float ripple = step(0.6, ripple_field) * step(ripple_field, 0.63) * ripple_amount;
	ALBEDO = mix(water.rgb, foam_color.rgb, max(foam, ripple));
	ALPHA = mix(water.a, foam_color.a, max(foam, ripple));
}
