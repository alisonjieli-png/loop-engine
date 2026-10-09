shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 holo_color : source_color = vec4(0.25, 0.85, 1.0, 1.0);
uniform float line_density : hint_range(10.0, 400.0) = 110.0;
uniform float line_speed : hint_range(-4.0, 4.0) = 0.5;
uniform float line_sharpness : hint_range(0.0, 1.0) = 0.6;
uniform float line_strength : hint_range(0.0, 1.0) = 0.4;
uniform float rim_power : hint_range(0.5, 8.0) = 2.0;
uniform float base_strength : hint_range(0.0, 1.0) = 0.18;
uniform float flicker_amount : hint_range(0.0, 1.0) = 0.3;
uniform float glitch_offset : hint_range(0.0, 0.3) = 0.05;
uniform float glitch_rate : hint_range(0.0, 20.0) = 5.0;
uniform float glitch_bands : hint_range(1.0, 40.0) = 10.0;

varying vec3 world_position;

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

float hash11(float x) {
	return float(fmix32(uint(int(floor(x)) + 1000000))) / 4294967295.0;
}

void vertex() {
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float slot = floor(TIME * glitch_rate);
	float band = floor(world.y * glitch_bands);
	float active = step(0.88, hash11(slot * 37.0 + band));
	VERTEX.x += active * (hash11(slot * 11.0 + band * 7.0) - 0.5) * 2.0 * glitch_offset;
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float wave = 0.5 + 0.5 * sin((world_position.y + TIME * line_speed) * line_density);
	float lines = mix(wave, step(0.5, wave), line_sharpness);
	float rim = pow(1.0 - abs(dot(NORMAL, VIEW)), rim_power);
	float flicker = 1.0 - flicker_amount * step(0.9, hash11(floor(TIME * 20.0)));
	ALBEDO = holo_color.rgb * (base_strength + rim + lines * line_strength) * flicker;
}
