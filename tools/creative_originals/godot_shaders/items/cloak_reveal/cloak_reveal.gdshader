shader_type spatial;
render_mode cull_back, depth_draw_always;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform vec4 albedo : source_color = vec4(0.6, 0.62, 0.66, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float cloak : hint_range(0.0, 1.0) = 0.55;
uniform float object_height : hint_range(0.1, 10.0) = 1.5;
uniform float distortion : hint_range(0.0, 0.1) = 0.025;
uniform float shimmer_speed : hint_range(0.0, 5.0) = 1.2;
uniform float edge_noise : hint_range(0.0, 1.0) = 0.25;
uniform vec4 seam_color : source_color = vec4(0.4, 0.9, 1.0, 1.0);
uniform float seam_width : hint_range(0.0, 0.2) = 0.04;
uniform float rim_visibility : hint_range(0.0, 1.0) = 0.3;

varying vec3 object_position;

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

float hash31(vec3 p) {
	ivec3 c = ivec3(floor(p));
	return float(fmix32(uint(c.x) * 73856093u ^ uint(c.y) * 19349663u ^ uint(c.z) * 83492791u)) / 4294967295.0;
}

float value_noise3(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	float n000 = hash31(cell);
	float n100 = hash31(cell + vec3(1.0, 0.0, 0.0));
	float n010 = hash31(cell + vec3(0.0, 1.0, 0.0));
	float n110 = hash31(cell + vec3(1.0, 1.0, 0.0));
	float n001 = hash31(cell + vec3(0.0, 0.0, 1.0));
	float n101 = hash31(cell + vec3(1.0, 0.0, 1.0));
	float n011 = hash31(cell + vec3(0.0, 1.0, 1.0));
	float n111 = hash31(cell + vec3(1.0, 1.0, 1.0));
	float x00 = mix(n000, n100, u.x);
	float x10 = mix(n010, n110, u.x);
	float x01 = mix(n001, n101, u.x);
	float x11 = mix(n011, n111, u.x);
	return mix(mix(x00, x10, u.y), mix(x01, x11, u.y), u.z);
}

float fbm3(vec3 p, int octaves) {
	float total = 0.0;
	float amplitude = 0.5;
	float norm = 0.0;
	for (int i = 0; i < octaves; i++) {
		total += amplitude * value_noise3(p);
		norm += amplitude;
		p = p * 2.07 + vec3(11.3, 5.7, 3.1);
		amplitude *= 0.5;
	}
	return total / norm;
}

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	float h = object_position.y / object_height + 0.5;
	float n = fbm3(object_position * 4.0, 3);
	float threshold = mix(-0.2, 1.2, cloak);
	float cloaked = step(h + (n - 0.5) * edge_noise, threshold);
	float seam = 1.0 - smoothstep(0.0, seam_width, abs(h + (n - 0.5) * edge_noise - threshold));
	vec3 shimmer = vec3(fbm3(object_position * 6.0 + TIME * shimmer_speed, 3),
						fbm3(object_position * 6.0 - TIME * shimmer_speed + 7.0, 3), 0.0) - 0.5;
	vec2 offset = (NORMAL.xy * 0.6 + shimmer.xy) * distortion;
	vec3 behind = textureLod(screen_texture, SCREEN_UV + offset, 0.0).rgb;
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0) * rim_visibility;
	ALBEDO = mix(albedo.rgb, vec3(0.0), cloaked);
	ROUGHNESS = roughness;
	EMISSION = cloaked * (behind * (1.0 - rim) + seam_color.rgb * rim * 0.5) + seam * seam_color.rgb * 3.0;
}
