shader_type canvas_item;

uniform vec4 shine_color : source_color = vec4(1.0, 1.0, 0.95, 1.0);
uniform float angle_degrees : hint_range(-90.0, 90.0) = 30.0;
uniform float band_width : hint_range(0.01, 0.6) = 0.14;
uniform float softness : hint_range(0.0, 1.0) = 0.5;
uniform float intensity : hint_range(0.0, 2.0) = 0.9;
uniform float sweep_time : hint_range(0.1, 5.0) = 0.8;
uniform float pause_time : hint_range(0.0, 10.0) = 1.4;
uniform float progress_override : hint_range(-1.0, 1.0) = -1.0;

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

void fragment() {
	vec4 source = texture(TEXTURE, UV) * tint;
	float cycle = sweep_time + pause_time;
	float progress = progress_override >= 0.0 ? progress_override : clamp(mod(TIME, cycle) / sweep_time, 0.0, 1.0);
	float angle = radians(angle_degrees);
	vec2 direction = vec2(cos(angle), sin(angle));
	float coordinate = dot(UV - 0.5, direction);
	float position = mix(-0.75 - band_width, 0.75 + band_width, progress);
	float distance_to_band = abs(coordinate - position);
	float band = 1.0 - smoothstep(band_width * (1.0 - softness), band_width, distance_to_band);
	COLOR = vec4(source.rgb + shine_color.rgb * band * intensity * source.a, source.a);
}
