shader_type spatial;

uniform float interval : hint_range(0.01, 50.0) = 0.1;
uniform int major_every : hint_range(1, 20) = 5;
uniform float line_pixels : hint_range(0.5, 4.0) = 1.0;
uniform vec4 line_color : source_color = vec4(0.35, 0.22, 0.12, 1.0);
uniform float height_low : hint_range(-100.0, 100.0) = -0.5;
uniform float height_high : hint_range(-100.0, 100.0) = 0.6;
uniform vec4 low_tint : source_color = vec4(0.55, 0.75, 0.5, 1.0);
uniform vec4 mid_tint : source_color = vec4(0.9, 0.85, 0.6, 1.0);
uniform vec4 high_tint : source_color = vec4(0.72, 0.55, 0.42, 1.0);
uniform int tint_steps : hint_range(0, 32) = 8;

varying vec3 world_position;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float contour(float value, float pixels) {
	float width = max(fwidth(value), 1e-5);
	float distance_pixels = abs(fract(value - 0.5) - 0.5) / width;
	return 1.0 - clamp(distance_pixels - pixels * 0.5 + 0.5, 0.0, 1.0);
}

void fragment() {
	float h = world_position.y;
	float t = clamp((h - height_low) / max(height_high - height_low, 1e-4), 0.0, 1.0);
	if (tint_steps > 0) {
		t = floor(t * float(tint_steps)) / float(tint_steps);
	}
	vec3 tint = t < 0.5 ? mix(low_tint.rgb, mid_tint.rgb, t * 2.0) : mix(mid_tint.rgb, high_tint.rgb, t * 2.0 - 1.0);
	float minor = contour(h / interval, line_pixels);
	float major = contour(h / (interval * float(major_every)), line_pixels * 2.0);
	ALBEDO = mix(tint, line_color.rgb, max(minor * 0.6, major));
	ROUGHNESS = 0.9;
}
