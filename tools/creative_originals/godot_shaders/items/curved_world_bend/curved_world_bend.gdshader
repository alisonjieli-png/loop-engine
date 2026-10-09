shader_type spatial;

uniform float curvature : hint_range(0.0, 0.2) = 0.02;
uniform float sideways_curvature : hint_range(-0.2, 0.2) = 0.0;
uniform float flat_radius : hint_range(0.0, 20.0) = 2.0;
uniform vec4 color_a : source_color = vec4(0.85, 0.82, 0.75, 1.0);
uniform vec4 color_b : source_color = vec4(0.35, 0.55, 0.75, 1.0);
uniform float checker_size : hint_range(0.1, 10.0) = 1.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.8;

varying vec3 world_position;

void vertex() {
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_position = world;
	vec3 camera_position = INV_VIEW_MATRIX[3].xyz;
	vec2 offset = world.xz - camera_position.xz;
	float distance_to_camera = max(length(offset) - flat_radius, 0.0);
	world.y -= curvature * distance_to_camera * distance_to_camera;
	world.x += sideways_curvature * distance_to_camera * distance_to_camera;
	VERTEX = (inverse(MODEL_MATRIX) * vec4(world, 1.0)).xyz;
}

void fragment() {
	vec3 cell = floor(world_position / checker_size + 0.001);
	float checker = mod(cell.x + cell.y + cell.z, 2.0);
	ALBEDO = mix(color_a.rgb, color_b.rgb, checker);
	ROUGHNESS = roughness;
}
