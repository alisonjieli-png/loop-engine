shader_type canvas_item;

uniform vec4 line_color : source_color = vec4(1.0, 0.95, 0.4, 1.0);
uniform int width : hint_range(1, 8) = 2;
uniform float alpha_cutoff : hint_range(0.01, 1.0) = 0.5;
uniform bool keep_interior = true;
uniform float pulse_speed : hint_range(0.0, 12.0) = 0.0;

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

float alpha_at(sampler2D tex, vec2 uv) {
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) {
		return 0.0;
	}
	return texture(tex, uv).a;
}

void fragment() {
	vec4 source = texture(TEXTURE, UV);
	if (source.a < alpha_cutoff) {
		COLOR = vec4(0.0);
	} else {
		float edge = 0.0;
		for (int y = -width; y <= width; y++) {
			for (int x = -width; x <= width; x++) {
				if (x * x + y * y <= width * width) {
					float a = alpha_at(TEXTURE, UV + vec2(float(x), float(y)) * TEXTURE_PIXEL_SIZE);
					edge = max(edge, step(a, alpha_cutoff - 0.001));
				}
			}
		}
		float pulse = pulse_speed > 0.0 ? 0.6 + 0.4 * sin(TIME * pulse_speed) : 1.0;
		vec4 interior = keep_interior ? source * tint : vec4(0.0);
		COLOR = mix(interior, line_color, edge * pulse);
	}
}
