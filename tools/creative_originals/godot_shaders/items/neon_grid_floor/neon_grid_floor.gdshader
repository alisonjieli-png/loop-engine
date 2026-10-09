shader_type spatial;
render_mode unshaded;

uniform vec4 near_color : source_color = vec4(1.0, 0.2, 0.75, 1.0);
uniform vec4 far_color : source_color = vec4(0.2, 0.8, 1.0, 1.0);
uniform vec4 floor_color : source_color = vec4(0.03, 0.0, 0.06, 1.0);
uniform vec4 haze_color : source_color = vec4(0.35, 0.05, 0.4, 1.0);
uniform float cell_size : hint_range(0.1, 10.0) = 1.0;
uniform float line_pixels : hint_range(0.5, 6.0) = 1.5;
uniform float glow_width : hint_range(0.0, 0.5) = 0.12;
uniform float scroll_speed : hint_range(-10.0, 10.0) = 1.5;
uniform float haze_distance : hint_range(1.0, 200.0) = 40.0;
uniform float intensity : hint_range(0.0, 4.0) = 1.6;

varying vec3 world_position;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 coordinate = world_position.xz / cell_size + vec2(0.0, TIME * scroll_speed);
	vec2 width = max(fwidth(coordinate), vec2(1e-5));
	vec2 distance_cells = abs(fract(coordinate - 0.5) - 0.5);
	vec2 distance_pixels = distance_cells / width;
	float line = 1.0 - clamp(min(distance_pixels.x, distance_pixels.y) - line_pixels * 0.5 + 0.5, 0.0, 1.0);
	float halo = 1.0 - smoothstep(0.0, glow_width, min(distance_cells.x, distance_cells.y));
	float distance_to_camera = length(VERTEX);
	float far = smoothstep(0.0, haze_distance, distance_to_camera);
	vec3 neon = mix(near_color.rgb, far_color.rgb, far);
	vec3 color = floor_color.rgb + neon * (line + halo * halo * 0.35) * intensity;
	ALBEDO = mix(color, haze_color.rgb, smoothstep(haze_distance * 0.4, haze_distance, distance_to_camera));
}
