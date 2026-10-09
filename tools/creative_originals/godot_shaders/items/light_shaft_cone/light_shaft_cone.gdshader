shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 beam_color : source_color = vec4(1.0, 0.92, 0.7, 1.0);
uniform float intensity : hint_range(0.0, 4.0) = 0.9;
uniform float edge_softness : hint_range(0.1, 8.0) = 2.5;
uniform float length_falloff : hint_range(0.0, 4.0) = 1.4;
uniform float dust_amount : hint_range(0.0, 1.0) = 0.5;
uniform float dust_scale : hint_range(5.0, 200.0) = 60.0;
uniform float dust_speed : hint_range(0.0, 1.0) = 0.05;
uniform float contact_fade : hint_range(0.01, 2.0) = 0.4;

varying vec3 object_position;

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
	float facing = abs(dot(NORMAL, VIEW));
	float edges = pow(facing, edge_softness);
	float along = clamp(UV.y, 0.0, 1.0);
	float falloff = exp(-along * length_falloff);
	float dust = value_noise3(object_position * dust_scale + vec3(0.0, -TIME * dust_speed * dust_scale, 0.0));
	dust = mix(1.0, smoothstep(0.7, 0.95, dust) * 2.0 + 0.6, dust_amount);
	float scene_depth = scene_view_depth(SCREEN_UV, INV_PROJECTION_MATRIX);
	float contact = clamp((scene_depth + VERTEX.z) / contact_fade, 0.0, 1.0);
	ALBEDO = beam_color.rgb * intensity * edges * falloff * dust * contact;
}
