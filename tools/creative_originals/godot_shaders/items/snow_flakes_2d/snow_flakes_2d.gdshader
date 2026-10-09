shader_type canvas_item;

uniform vec4 snow_color : source_color = vec4(1.0, 1.0, 1.0, 0.9);
uniform float density : hint_range(0.0, 1.0) = 0.55;
uniform float fall_speed : hint_range(0.0, 2.0) = 0.15;
uniform float sway : hint_range(0.0, 1.0) = 0.35;
uniform float wind : hint_range(-1.0, 1.0) = 0.1;
uniform float flake_scale : hint_range(4.0, 60.0) = 14.0;
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

float snow_layer(vec2 uv, float scale, float speed, float size, float salt) {
	vec2 p = vec2(uv.x * aspect, uv.y) * flake_scale * scale;
	p.y -= TIME * fall_speed * speed * flake_scale * scale;
	p.x -= TIME * wind * flake_scale * scale * speed;
	vec2 cell = floor(p);
	vec2 local = fract(p);
	float present = step(1.0 - density, hash21(cell + salt));
	vec2 center = 0.2 + hash22(cell + salt * 3.0) * 0.6;
	center.x += sin(TIME * (1.0 + hash21(cell + salt) * 2.0) + cell.y) * sway * 0.25;
	float radius = size * mix(0.5, 1.0, hash21(cell + salt * 5.0));
	float flake = 1.0 - smoothstep(radius * 0.4, radius, length(local - center));
	return flake * present;
}

void fragment() {
	float near = snow_layer(UV, 1.0, 1.0, 0.16, 1.0);
	float middle = snow_layer(UV, 1.8, 0.7, 0.14, 7.0) * 0.7;
	float far = snow_layer(UV, 3.2, 0.45, 0.12, 19.0) * 0.45;
	float snow = clamp(near + middle + far, 0.0, 1.0);
	COLOR = vec4(snow_color.rgb, snow * snow_color.a);
}
