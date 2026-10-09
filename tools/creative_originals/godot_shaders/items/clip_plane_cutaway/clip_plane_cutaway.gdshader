shader_type spatial;
render_mode cull_disabled;

uniform vec4 albedo : source_color = vec4(0.35, 0.55, 0.85, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.45;
uniform vec4 cap_color : source_color = vec4(0.9, 0.3, 0.25, 1.0);
uniform vec4 edge_color : source_color = vec4(1.0, 0.85, 0.4, 1.0);
uniform float plane_pitch_degrees : hint_range(-90.0, 90.0) = 0.0;
uniform float plane_yaw_degrees : hint_range(-180.0, 180.0) = 35.0;
uniform float plane_offset : hint_range(-10.0, 10.0) = 0.0;
uniform float edge_width : hint_range(0.0, 0.2) = 0.02;
uniform float sweep_speed : hint_range(0.0, 2.0) = 0.0;
uniform float sweep_range : hint_range(0.0, 10.0) = 0.5;

varying vec3 world_position;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float pitch = radians(plane_pitch_degrees);
	float yaw = radians(plane_yaw_degrees);
	vec3 plane_normal = vec3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch));
	float offset = plane_offset + sin(TIME * sweep_speed) * sweep_range * step(0.0001, sweep_speed);
	float side = dot(world_position, plane_normal) - offset;
	if (side > 0.0) {
		discard;
	}
	float edge = 1.0 - smoothstep(0.0, edge_width, -side);
	if (FRONT_FACING) {
		ALBEDO = albedo.rgb;
		ROUGHNESS = roughness;
		EMISSION = edge_color.rgb * edge * 2.0;
	} else {
		NORMAL = (VIEW_MATRIX * vec4(-plane_normal, 0.0)).xyz;
		ALBEDO = cap_color.rgb;
		ROUGHNESS = 0.9;
		EMISSION = cap_color.rgb * 0.25 + edge_color.rgb * edge;
	}
}
