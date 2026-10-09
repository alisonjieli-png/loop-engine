shader_type spatial;
render_mode unshaded;

uniform int mode : hint_range(0, 7) = 0;
uniform float depth_band : hint_range(0.05, 10.0) = 0.5;
uniform float position_cell : hint_range(0.05, 10.0) = 0.25;
uniform bool flip_back_faces = true;

varying vec3 vertex_world_normal;
varying vec4 vertex_color;

void vertex() {
	vertex_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vertex_color = COLOR;
}

void fragment() {
	vec3 view_normal = normalize(NORMAL);
	if (flip_back_faces && !FRONT_FACING) {
		view_normal = -view_normal;
	}
	vec3 world_normal = normalize((INV_VIEW_MATRIX * vec4(view_normal, 0.0)).xyz);
	vec3 world_tangent = normalize((INV_VIEW_MATRIX * vec4(TANGENT, 0.0)).xyz);
	vec3 world_binormal = normalize((INV_VIEW_MATRIX * vec4(BINORMAL, 0.0)).xyz);
	vec3 world_position = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 color = vec3(0.0);
	if (mode == 0) {
		color = world_normal * 0.5 + 0.5;
	} else if (mode == 1) {
		color = view_normal * 0.5 + 0.5;
	} else if (mode == 2) {
		color = world_tangent * 0.5 + 0.5;
	} else if (mode == 3) {
		color = world_binormal * 0.5 + 0.5;
	} else if (mode == 4) {
		color = vec3(fract(UV), 0.0);
	} else if (mode == 5) {
		color = vertex_color.rgb;
	} else if (mode == 6) {
		float depth = -VERTEX.z / depth_band;
		color = vec3(fract(depth), fract(depth * 0.25), 1.0 - fract(depth * 0.0625));
	} else {
		vec3 cell = floor(world_position / position_cell);
		color = fract(cell * vec3(0.137, 0.271, 0.419) + 0.5);
	}
	ALBEDO = color;
}
