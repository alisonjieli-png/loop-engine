shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_nearest;
uniform sampler2D palette : source_color, filter_nearest, repeat_disable;
uniform int palette_size : hint_range(2, 32) = 8;
uniform float pixel_size : hint_range(1.0, 32.0) = 4.0;
uniform float dither_strength : hint_range(0.0, 1.0) = 0.35;
uniform float palette_mix : hint_range(0.0, 1.0) = 1.0;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

vec3 nearest_palette_color(vec3 color) {
	vec3 best = color;
	float best_distance = 1e9;
	for (int i = 0; i < palette_size; i++) {
		vec3 candidate = texture(palette, vec2((float(i) + 0.5) / float(palette_size), 0.5)).rgb;
		vec3 delta = (color - candidate) * vec3(0.3, 0.59, 0.11);
		float distance_squared = dot(delta, delta) + dot(color - candidate, color - candidate) * 0.1;
		if (distance_squared < best_distance) {
			best_distance = distance_squared;
			best = candidate;
		}
	}
	return best;
}

void fragment() {
	vec2 block = floor(FRAGCOORD.xy / pixel_size);
	vec2 center = (block + 0.5) * pixel_size / VIEWPORT_SIZE;
	vec3 color = texture(screen_texture, center).rgb;
	ivec2 cell = ivec2(mod(block, 2.0));
	float threshold = (float(cell.x * 2 + cell.y * 3 - (cell.x * cell.y) * 4) / 4.0 + 0.125) - 0.5;
	vec3 dithered = clamp(color + threshold * dither_strength * 0.25, 0.0, 1.0);
	ALBEDO = mix(color, nearest_palette_color(dithered), palette_mix);
}
