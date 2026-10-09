shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform vec4 phosphor : source_color = vec4(0.35, 1.0, 0.45, 1.0);
uniform float gain : hint_range(0.5, 6.0) = 2.4;
uniform float glow : hint_range(0.0, 2.0) = 0.6;
uniform float noise_amount : hint_range(0.0, 1.0) = 0.25;
uniform float scanline_strength : hint_range(0.0, 1.0) = 0.15;
uniform bool binocular = true;
uniform float mask_radius : hint_range(0.2, 1.0) = 0.46;

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

void fragment() {
	vec3 scene = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 blurred = textureLod(screen_texture, SCREEN_UV, 3.0).rgb;
	float l = luminance(scene) * gain + luminance(blurred) * glow;
	float frame = floor(TIME * 30.0);
	float noise = hash21(FRAGCOORD.xy + vec2(frame * 13.0, frame * 7.0)) - 0.5;
	l += noise * noise_amount;
	l *= 1.0 - scanline_strength * step(0.5, fract(FRAGCOORD.y * 0.5));
	float aspect = VIEWPORT_SIZE.x / VIEWPORT_SIZE.y;
	vec2 p = (SCREEN_UV - 0.5) * vec2(aspect, 1.0);
	float mask;
	if (binocular) {
		float left = length(p - vec2(-0.2 * aspect, 0.0));
		float right = length(p - vec2(0.2 * aspect, 0.0));
		mask = 1.0 - smoothstep(mask_radius - 0.03, mask_radius, min(left, right) / max(aspect * 0.5, 0.5) * 1.0);
	} else {
		mask = 1.0 - smoothstep(mask_radius - 0.03, mask_radius, length(p));
	}
	float vignette = 1.0 - smoothstep(0.2, 0.75, length(p));
	ALBEDO = phosphor.rgb * clamp(l, 0.0, 1.5) * mask * mix(0.5, 1.0, vignette);
}
