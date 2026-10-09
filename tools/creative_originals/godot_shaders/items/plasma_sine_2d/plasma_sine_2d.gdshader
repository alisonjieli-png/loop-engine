shader_type canvas_item;

uniform float scale : hint_range(1.0, 30.0) = 8.0;
uniform float speed : hint_range(0.0, 5.0) = 1.0;
uniform vec4 palette_offset : source_color = vec4(0.5, 0.5, 0.5, 1.0);
uniform vec4 palette_amplitude : source_color = vec4(0.5, 0.5, 0.5, 1.0);
uniform vec4 palette_frequency : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 palette_phase : source_color = vec4(0.0, 0.33, 0.67, 1.0);
uniform float cycle_speed : hint_range(0.0, 2.0) = 0.15;
uniform int color_steps : hint_range(0, 32) = 0;

vec3 cosine_palette(float t) {
	return palette_offset.rgb + palette_amplitude.rgb * cos(TAU * (palette_frequency.rgb * t + palette_phase.rgb));
}

void fragment() {
	vec2 p = (UV - 0.5) * scale;
	float t = TIME * speed;
	float value = sin(p.x + t);
	value += sin(p.y * 0.8 + t * 1.3);
	value += sin((p.x + p.y) * 0.7 + t * 0.7);
	value += sin(length(p + vec2(sin(t * 0.5), cos(t * 0.4)) * 2.0) * 1.5 - t);
	float level = value * 0.125 + 0.5 + TIME * cycle_speed;
	if (color_steps > 0) {
		level = floor(level * float(color_steps)) / float(color_steps);
	}
	COLOR = vec4(cosine_palette(level), 1.0);
}
