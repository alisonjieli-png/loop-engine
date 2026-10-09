shader_type canvas_item;

uniform vec4 shadow_color : source_color = vec4(0.0, 0.0, 0.05, 0.6);
uniform float offset_x : hint_range(-32.0, 32.0) = 7.0;
uniform float offset_y : hint_range(-32.0, 32.0) = 7.0;
uniform float softness : hint_range(0.0, 8.0) = 2.5;

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
	vec2 shadow_uv = UV - vec2(offset_x, offset_y) * TEXTURE_PIXEL_SIZE;
	float shadow = 0.0;
	float weights = 0.0;
	for (int y = -2; y <= 2; y++) {
		for (int x = -2; x <= 2; x++) {
			float w = exp(-float(x * x + y * y) * 0.35);
			shadow += alpha_at(TEXTURE, shadow_uv + vec2(float(x), float(y)) * softness * 0.5 * TEXTURE_PIXEL_SIZE) * w;
			weights += w;
		}
	}
	float shadow_alpha = shadow / weights * shadow_color.a;
	float out_alpha = source.a + shadow_alpha * (1.0 - source.a);
	vec3 out_color = (source.rgb * source.a + shadow_color.rgb * shadow_alpha * (1.0 - source.a)) / max(out_alpha, 1e-4);
	COLOR = vec4(out_color, out_alpha);
}
