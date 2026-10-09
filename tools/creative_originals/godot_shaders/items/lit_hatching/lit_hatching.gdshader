shader_type spatial;

uniform vec4 paper_color : source_color = vec4(0.96, 0.94, 0.88, 1.0);
uniform float line_density : hint_range(10.0, 400.0) = 90.0;
uniform float line_width : hint_range(0.05, 0.9) = 0.35;
uniform float level_1 : hint_range(0.0, 1.0) = 0.8;
uniform float level_2 : hint_range(0.0, 1.0) = 0.55;
uniform float level_3 : hint_range(0.0, 1.0) = 0.32;
uniform float level_4 : hint_range(0.0, 1.0) = 0.15;
uniform float ink_strength : hint_range(0.0, 1.0) = 0.92;

float hatch_lines(vec2 uv, float angle_degrees) {
	float angle = radians(angle_degrees);
	float coordinate = dot(uv, vec2(cos(angle), sin(angle))) * line_density;
	float distance_to_line = abs(fract(coordinate) - 0.5);
	float width = fwidth(coordinate);
	return 1.0 - smoothstep(line_width * 0.5 - width, line_width * 0.5 + width, distance_to_line);
}

void fragment() {
	ALBEDO = paper_color.rgb;
}

void light() {
	float tone = clamp(dot(NORMAL, LIGHT), 0.0, 1.0) * ATTENUATION;
	float ink = 0.0;
	ink = max(ink, hatch_lines(UV, 45.0) * step(tone, level_1));
	ink = max(ink, hatch_lines(UV, -45.0) * step(tone, level_2));
	ink = max(ink, hatch_lines(UV, 0.0) * step(tone, level_3));
	ink = max(ink, hatch_lines(UV * 1.7, 90.0) * step(tone, level_4));
	DIFFUSE_LIGHT += (1.0 - ink * ink_strength) * LIGHT_COLOR / PI;
}
