shader_type canvas_item;

uniform vec4 dash_dark : source_color = vec4(0.05, 0.05, 0.05, 1.0);
uniform vec4 dash_light : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float dash_pixels : hint_range(2.0, 32.0) = 6.0;
uniform float speed : hint_range(-40.0, 40.0) = 12.0;
uniform int width : hint_range(1, 4) = 1;
uniform bool outside = true;
uniform float alpha_cutoff : hint_range(0.01, 1.0) = 0.5;

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
	bool inside = source.a >= alpha_cutoff;
	float edge = 0.0;
	for (int y = -width; y <= width; y++) {
		for (int x = -width; x <= width; x++) {
			float a = alpha_at(TEXTURE, UV + vec2(float(x), float(y)) * TEXTURE_PIXEL_SIZE);
			bool other = a >= alpha_cutoff;
			if (other != inside) {
				edge = 1.0;
			}
		}
	}
	bool on_line = edge > 0.5 && (outside ? !inside : inside);
	float dash = step(0.5, fract((FRAGCOORD.x + FRAGCOORD.y) / (dash_pixels * 2.0) - TIME * speed / (dash_pixels * 2.0)));
	vec4 line = mix(dash_dark, dash_light, dash);
	COLOR = on_line ? line : source;
}
