shader_type canvas_item;

uniform float edge_sharpness : hint_range(0.25, 4.0) = 1.0;
uniform bool enabled = true;

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

void fragment() {
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 texel = UV * size;
	vec2 uv = UV;
	if (enabled) {
		vec2 nearest_edge = floor(texel + 0.5);
		vec2 per_pixel = max(fwidth(texel), vec2(1e-5)) / edge_sharpness;
		vec2 offset = clamp((texel - nearest_edge) / per_pixel, -0.5, 0.5);
		uv = (nearest_edge + offset) / size;
	}
	COLOR = texture(TEXTURE, uv) * tint;
}
