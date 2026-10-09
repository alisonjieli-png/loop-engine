shader_type canvas_item;

uniform vec4 color_a : source_color = vec4(0.95, 0.4, 0.2, 1.0);
uniform vec4 color_b : source_color = vec4(0.15, 0.1, 0.35, 1.0);
uniform float speed : hint_range(-4.0, 4.0) = 1.2;
uniform float twist : hint_range(-2.0, 2.0) = 0.3;
uniform int segments : hint_range(2, 32) = 12;
uniform float depth_rings : hint_range(1.0, 20.0) = 6.0;
uniform float fog : hint_range(0.0, 4.0) = 1.4;
uniform float center_x : hint_range(-0.5, 0.5) = 0.0;
uniform float center_y : hint_range(-0.5, 0.5) = 0.0;

void fragment() {
	vec2 p = UV - 0.5 - vec2(center_x, center_y) + vec2(sin(TIME * 0.7), cos(TIME * 0.5)) * 0.05;
	float radius = max(length(p), 1e-3);
	float angle = atan(p.y, p.x) / TAU + 0.5;
	float depth = 0.3 / radius;
	vec2 wall = vec2(angle + depth * twist * 0.1 + TIME * 0.02, depth + TIME * speed);
	vec2 cells = floor(vec2(wall.x * float(segments), wall.y * depth_rings));
	float checker = mod(cells.x + cells.y, 2.0);
	vec3 color = mix(color_a.rgb, color_b.rgb, checker);
	float shade = exp(-depth * fog * 0.3) * smoothstep(0.0, 0.05, radius);
	COLOR = vec4(color * shade, 1.0);
}
