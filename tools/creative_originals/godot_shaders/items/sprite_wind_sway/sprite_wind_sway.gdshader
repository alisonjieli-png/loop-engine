shader_type canvas_item;

uniform float strength : hint_range(0.0, 64.0) = 14.0;
uniform float speed : hint_range(0.0, 10.0) = 1.6;
uniform float gust_strength : hint_range(0.0, 64.0) = 10.0;
uniform float gust_wavelength : hint_range(50.0, 2000.0) = 600.0;
uniform float gust_speed : hint_range(0.0, 1000.0) = 220.0;
uniform float stiffness : hint_range(0.5, 4.0) = 1.5;
uniform float base_v : hint_range(0.0, 1.0) = 1.0;

varying vec4 tint;

void vertex() {
	tint = COLOR;
	vec2 origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xy;
	float height = clamp(abs(base_v - UV.y), 0.0, 1.0);
	float bend = pow(height, stiffness);
	float sway = sin(TIME * speed + origin.x * 0.05) * strength;
	float gust = max(sin((origin.x - TIME * gust_speed) / gust_wavelength * TAU), 0.0) * gust_strength;
	VERTEX.x += (sway + gust) * bend;
}

void fragment() {
	COLOR = texture(TEXTURE, UV) * tint;
}
