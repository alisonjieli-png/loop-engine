shader_type spatial;

uniform vec4 print_color : source_color = vec4(0.12, 0.14, 0.3, 1.0);
uniform float foil_strength : hint_range(0.0, 1.0) = 0.8;
uniform float band_frequency : hint_range(0.5, 20.0) = 4.0;
uniform float view_shift : hint_range(0.0, 10.0) = 3.0;
uniform float tile_count : hint_range(1.0, 60.0) = 14.0;
uniform float tile_contrast : hint_range(0.0, 1.0) = 0.5;
uniform float sparkle_density : hint_range(0.0, 1.0) = 0.15;
uniform float saturation : hint_range(0.0, 1.0) = 0.85;

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

vec3 hue_to_rgb(float hue) {
	vec3 rgb = clamp(abs(mod(hue * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
	return mix(vec3(1.0), rgb, saturation);
}

void fragment() {
	vec3 view_tangent = normalize(vec3(dot(VIEW, TANGENT), dot(VIEW, -BINORMAL), dot(VIEW, NORMAL)));
	vec2 tile = floor(UV * tile_count);
	float angle = hash21(tile) * PI;
	vec2 grating = vec2(cos(angle), sin(angle));
	float tile_phase = dot(view_tangent.xy, grating) * view_shift * 2.0;
	float sweep = dot(UV, vec2(0.7, 0.4)) * band_frequency + view_tangent.x * view_shift;
	float hue = fract(sweep + tile_phase * tile_contrast);
	vec3 rainbow = hue_to_rgb(hue);
	float sparkle_cell = hash21(floor(UV * 180.0) + vec2(9.0, 1.0));
	float sparkle = step(1.0 - sparkle_density * 0.1, sparkle_cell)
		* step(0.6, fract(sparkle_cell * 13.0 + view_tangent.x * 4.0 + view_tangent.y * 3.0));
	ALBEDO = mix(print_color.rgb, rainbow, foil_strength) + vec3(sparkle);
	METALLIC = foil_strength;
	ROUGHNESS = 0.25;
}
