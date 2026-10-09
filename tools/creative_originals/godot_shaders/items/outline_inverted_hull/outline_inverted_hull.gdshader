shader_type spatial;
render_mode unshaded, cull_front, shadows_disabled, fog_disabled;

uniform vec4 outline_color : source_color = vec4(0.04, 0.03, 0.07, 1.0);
uniform float thickness : hint_range(0.0, 0.2) = 0.015;
uniform float distance_scaling : hint_range(0.0, 1.0) = 0.6;
uniform float max_thickness : hint_range(0.0, 0.5) = 0.08;

void vertex() {
	vec3 view_position = (MODELVIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float distance_factor = mix(1.0, max(-view_position.z, 0.0), distance_scaling);
	float width = min(thickness * distance_factor, max_thickness);
	VERTEX += normalize(NORMAL) * width;
}

void fragment() {
	ALBEDO = outline_color.rgb;
}
