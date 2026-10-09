shader_type canvas_item;

uniform vec4 glow_color : source_color = vec4(0.4, 0.85, 1.0, 1.0);
uniform float radius : hint_range(1.0, 24.0) = 10.0;
uniform float intensity : hint_range(0.0, 4.0) = 1.6;
uniform int rings : hint_range(1, 6) = 3;
uniform int directions : hint_range(4, 24) = 12;
uniform float pulse_speed : hint_range(0.0, 10.0) = 2.0;
uniform float pulse_depth : hint_range(0.0, 1.0) = 0.3;

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
	vec4 source = texture(TEXTURE, UV) * tint;
	float gathered = 0.0;
	float weights = 0.0;
	for (int r = 1; r <= rings; r++) {
		float distance_texels = radius * float(r) / float(rings);
		float weight = 1.0 - float(r - 1) / float(rings);
		for (int d = 0; d < directions; d++) {
			float angle = TAU * (float(d) + 0.5 * float(r)) / float(directions);
			vec2 offset = vec2(cos(angle), sin(angle)) * distance_texels * TEXTURE_PIXEL_SIZE;
			gathered += alpha_at(TEXTURE, UV + offset) * weight;
			weights += weight;
		}
	}
	float pulse = 1.0 - pulse_depth * (0.5 + 0.5 * sin(TIME * pulse_speed));
	float glow = clamp(gathered / weights * intensity * pulse, 0.0, 1.0) * glow_color.a;
	float out_alpha = source.a + glow * (1.0 - source.a);
	vec3 out_color = (source.rgb * source.a + glow_color.rgb * glow * (1.0 - source.a)) / max(out_alpha, 1e-4);
	COLOR = vec4(out_color, out_alpha);
}
