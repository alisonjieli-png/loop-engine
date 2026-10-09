shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform float radius : hint_range(0.05, 3.0) = 0.45;
uniform float intensity : hint_range(0.0, 4.0) = 1.4;
uniform int samples : hint_range(4, 32) = 16;
uniform float bias : hint_range(0.0, 0.3) = 0.03;
uniform float max_pixels : hint_range(4.0, 128.0) = 48.0;
uniform vec4 shadow_tint : source_color = vec4(0.0, 0.0, 0.05, 1.0);
uniform bool show_occlusion = false;

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

// View-space position of the opaque scene at a screen position.
vec3 scene_view_position(vec2 screen_uv, mat4 inv_projection) {
	float raw = texture(depth_texture, screen_uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw * 2.0 - 1.0);
#else
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return view.xyz / view.w;
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 scene = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 p = scene_view_position(SCREEN_UV, INV_PROJECTION_MATRIX);
	vec3 n = normalize(cross(dFdx(p), dFdy(p)));
	if (dot(n, -p) < 0.0) {
		n = -n;
	}
	float pixels_per_unit = VIEWPORT_SIZE.y * 0.5 * PROJECTION_MATRIX[1][1];
	float screen_radius = min(radius * pixels_per_unit / max(-p.z, 0.05), max_pixels);
	float rotation = hash21(FRAGCOORD.xy) * TAU;
	float occlusion = 0.0;
	for (int i = 0; i < samples; i++) {
		float t = (float(i) + 0.5) / float(samples);
		float angle = float(i) * 2.39996323 + rotation;
		vec2 offset = vec2(cos(angle), sin(angle)) * sqrt(t) * screen_radius;
		vec3 q = scene_view_position(SCREEN_UV + offset / VIEWPORT_SIZE, INV_PROJECTION_MATRIX);
		vec3 v = q - p;
		float d = length(v);
		float facing = max(dot(n, v / max(d, 1e-4)) - bias, 0.0);
		float in_range = 1.0 - smoothstep(radius * 0.5, radius, d);
		occlusion += facing * in_range;
	}
	float ambient = clamp(1.0 - intensity * occlusion / float(samples), 0.0, 1.0);
	vec3 shaded = mix(shadow_tint.rgb, scene, ambient);
	ALBEDO = show_occlusion ? vec3(ambient) : shaded;
}
