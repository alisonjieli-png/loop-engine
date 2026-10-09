shader_type canvas_item;

uniform vec4 outline_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform int thickness : hint_range(0, 8) = 2;
uniform float alpha_cutoff : hint_range(0.01, 1.0) = 0.5;
uniform bool rounded = true;
uniform bool outline_only = false;

void fragment() {
	vec4 source = texture(TEXTURE, UV);
	bool inside = source.a >= alpha_cutoff;
	float coverage = 0.0;
	if (!inside && thickness > 0) {
		float limit = rounded ? float(thickness * thickness) + 0.5 : float(thickness);
		for (int y = -thickness; y <= thickness; y++) {
			for (int x = -thickness; x <= thickness; x++) {
				float distance = rounded ? float(x * x + y * y) : float(abs(x) + abs(y));
				if (distance <= limit) {
					vec2 offset = vec2(float(x), float(y)) * TEXTURE_PIXEL_SIZE;
					coverage = max(coverage, step(alpha_cutoff, texture(TEXTURE, UV + offset).a));
				}
			}
		}
	}
	vec4 line = vec4(outline_color.rgb, outline_color.a * coverage);
	if (inside) {
		COLOR = outline_only ? vec4(0.0) : source;
	} else {
		COLOR = line;
	}
}
