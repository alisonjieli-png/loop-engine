shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float amount : hint_range(0.0, 1.0) = 0.35;
uniform float grain_size : hint_range(1.0, 6.0) = 1.6;
uniform float color_grain : hint_range(0.0, 1.0) = 0.25;
uniform float midtone_bias : hint_range(0.0, 1.0) = 0.7;
uniform float frames_per_second : hint_range(1.0, 60.0) = 24.0;
uniform float flicker : hint_range(0.0, 0.2) = 0.03;

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

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float grain_sample(vec2 pixel, float frame, float salt) {
	vec2 cell = floor(pixel / grain_size);
	return hash21(cell + vec2(frame * 17.0 + salt, frame * 29.0 - salt)) - 0.5;
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	float frame = floor(TIME * frames_per_second);
	float mono = grain_sample(FRAGCOORD.xy, frame, 0.0);
	vec3 chroma = vec3(grain_sample(FRAGCOORD.xy, frame, 11.0), grain_sample(FRAGCOORD.xy, frame, 23.0),
					   grain_sample(FRAGCOORD.xy, frame, 37.0));
	vec3 grain = mix(vec3(mono), chroma, color_grain);
	float l = luminance(color);
	float response = mix(1.0, 4.0 * l * (1.0 - l), midtone_bias);
	float exposure = 1.0 + (hash21(vec2(frame, 7.0)) - 0.5) * flicker;
	ALBEDO = clamp(color * exposure + grain * amount * response, 0.0, 1.0);
}
