shader_type canvas_item;

uniform vec4 rain_color : source_color = vec4(0.75, 0.82, 0.95, 0.55);
uniform float density : hint_range(0.0, 1.0) = 0.5;
uniform float speed : hint_range(0.0, 5.0) = 1.6;
uniform float slant : hint_range(-1.0, 1.0) = 0.25;
uniform float streak_length : hint_range(0.02, 0.5) = 0.12;
uniform float columns : hint_range(10.0, 300.0) = 90.0;
uniform float aspect : hint_range(0.2, 5.0) = 1.0;

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

float rain_layer(vec2 uv, float scale, float layer_speed, float salt) {
	vec2 p = vec2(uv.x * aspect + uv.y * slant, uv.y);
	p.x *= columns * scale;
	float column = floor(p.x);
	float offset = hash21(vec2(column, salt));
	float speed_variation = mix(0.8, 1.2, hash21(vec2(column, salt + 1.0)));
	float y = fract(p.y * 0.6 / scale - TIME * speed * layer_speed * speed_variation + offset);
	float present = step(1.0 - density, hash21(vec2(column, salt + 2.0)));
	float thin = 1.0 - smoothstep(0.05, 0.25, abs(fract(p.x) - 0.5));
	float drop = smoothstep(streak_length * scale, 0.0, y) * step(0.0, y);
	return drop * thin * present;
}

void fragment() {
	float a = rain_layer(UV, 1.0, 1.0, 3.0);
	float b = rain_layer(UV, 0.6, 0.7, 11.0) * 0.6;
	float c = rain_layer(UV, 0.35, 0.45, 23.0) * 0.35;
	float rain = clamp(a + b + c, 0.0, 1.0);
	COLOR = vec4(rain_color.rgb, rain * rain_color.a);
}
