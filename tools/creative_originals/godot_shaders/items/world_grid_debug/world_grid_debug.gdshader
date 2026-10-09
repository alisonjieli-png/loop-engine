shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.32, 0.34, 0.38, 1.0);
uniform vec4 minor_color : source_color = vec4(0.48, 0.5, 0.55, 1.0);
uniform vec4 major_color : source_color = vec4(0.82, 0.84, 0.88, 1.0);
uniform float cell_size : hint_range(0.05, 10.0) = 0.5;
uniform int major_every : hint_range(1, 20) = 4;
uniform float line_pixels : hint_range(0.5, 4.0) = 1.2;
uniform bool show_axes = true;
uniform float fade_distance : hint_range(1.0, 200.0) = 40.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.8;

varying vec3 world_position;
varying vec3 world_normal;

float grid_line(vec2 coordinate, float width) {
	vec2 derivative = max(fwidth(coordinate), vec2(1e-5));
	vec2 distance_pixels = abs(fract(coordinate - 0.5) - 0.5) / derivative;
	return 1.0 - clamp(min(distance_pixels.x, distance_pixels.y) - width * 0.5 + 0.5, 0.0, 1.0);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 n = abs(world_normal);
	vec2 plane = n.y >= n.x && n.y >= n.z ? world_position.xz : (n.x >= n.z ? world_position.zy : world_position.xy);
	vec2 cells = plane / cell_size;
	float minor = grid_line(cells, line_pixels);
	float major = grid_line(cells / float(major_every), line_pixels * 1.6);
	float fade = 1.0 - smoothstep(fade_distance * 0.5, fade_distance, length(VERTEX));
	vec3 color = mix(base_color.rgb, minor_color.rgb, minor * fade);
	color = mix(color, major_color.rgb, major * fade);
	if (show_axes && n.y >= n.x && n.y >= n.z) {
		float x_axis = grid_line(vec2(world_position.z / cell_size, 0.5), line_pixels * 2.0);
		float z_axis = grid_line(vec2(world_position.x / cell_size, 0.5), line_pixels * 2.0);
		color = mix(color, vec3(0.9, 0.2, 0.2), x_axis * step(abs(world_position.z), cell_size * 0.5));
		color = mix(color, vec3(0.2, 0.4, 0.95), z_axis * step(abs(world_position.x), cell_size * 0.5));
	}
	ALBEDO = color;
	ROUGHNESS = roughness;
}
