shader_type canvas_item;

uniform float split : hint_range(0.0, 0.1) = 0.02;
uniform float slice_strength : hint_range(0.0, 0.3) = 0.08;
uniform float slice_count : hint_range(2.0, 64.0) = 18.0;
uniform float glitch_rate : hint_range(0.0, 30.0) = 8.0;
uniform float glitch_share : hint_range(0.0, 1.0) = 0.25;
uniform float band_flash : hint_range(0.0, 1.0) = 0.3;

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

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

float alpha_at(sampler2D tex, vec2 uv) {
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) {
		return 0.0;
	}
	return texture(tex, uv).a;
}

void fragment() {
	float slot = floor(TIME * glitch_rate);
	float slice = floor(UV.y * slice_count);
	float active = step(1.0 - glitch_share, hash21(vec2(slice, slot)));
	float shift = active * (hash21(vec2(slice * 3.0, slot + 7.0)) - 0.5) * 2.0 * slice_strength;
	vec2 uv = UV + vec2(shift, 0.0);
	float offset = split * (0.5 + hash21(vec2(slot, 11.0)));
	vec4 red = texture(TEXTURE, uv + vec2(offset, 0.0)) * alpha_at(TEXTURE, uv + vec2(offset, 0.0));
	vec4 green = texture(TEXTURE, uv) * alpha_at(TEXTURE, uv);
	vec4 blue = texture(TEXTURE, uv - vec2(offset, 0.0)) * alpha_at(TEXTURE, uv - vec2(offset, 0.0));
	float alpha = max(max(red.a, green.a), blue.a);
	vec3 color = vec3(red.r, green.g, blue.b) / max(alpha, 1e-4);
	float band = step(0.94, hash21(vec2(floor(UV.y * 60.0), slot + 3.0))) * band_flash;
	COLOR = vec4(color + band, alpha) * tint;
}
