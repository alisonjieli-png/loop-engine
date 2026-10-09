shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float center_x : hint_range(0.0, 1.0) = 0.5;
uniform float center_y : hint_range(0.0, 1.0) = 0.5;
uniform float strength : hint_range(0.0, 0.5) = 0.12;
uniform int samples : hint_range(2, 48) = 20;
uniform float clear_radius : hint_range(0.0, 1.0) = 0.15;
uniform float streak_boost : hint_range(0.0, 1.0) = 0.15;

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

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 center = vec2(center_x, center_y);
	vec2 to_center = center - SCREEN_UV;
	float distance_to_center = length(to_center);
	float amount = strength * smoothstep(clear_radius * 0.5, clear_radius + 0.25, distance_to_center);
	float jitter = hash21(FRAGCOORD.xy) / float(samples);
	vec3 total = vec3(0.0);
	for (int i = 0; i < samples; i++) {
		float t = (float(i) / float(samples) + jitter) * amount;
		total += textureLod(screen_texture, SCREEN_UV + to_center * t, 0.0).rgb;
	}
	vec3 color = total / float(samples);
	ALBEDO = color * (1.0 + streak_boost * amount / max(strength, 1e-4));
}
