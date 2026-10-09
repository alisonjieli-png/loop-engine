shader_type canvas_item;

uniform float amount : hint_range(0.0, 0.8) = 0.22;
uniform float speed : hint_range(0.0, 20.0) = 5.0;
uniform float pivot_u : hint_range(0.0, 1.0) = 0.5;
uniform float pivot_v : hint_range(0.0, 1.0) = 1.0;
uniform bool use_fixed_stretch = false;
uniform float fixed_stretch : hint_range(-0.8, 0.8) = 0.0;
uniform float hop_height : hint_range(0.0, 200.0) = 24.0;

varying vec4 tint;

void vertex() {
	tint = COLOR;
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 pivot = VERTEX - (UV - vec2(pivot_u, pivot_v)) * size;
	float phase = fract(TIME * speed / TAU);
	float stretch = use_fixed_stretch ? fixed_stretch : amount * cos(phase * TAU);
	float scale_y = 1.0 + stretch;
	float scale_x = 1.0 / sqrt(max(scale_y, 0.1));
	vec2 local = VERTEX - pivot;
	VERTEX = pivot + local * vec2(scale_x, scale_y);
	if (!use_fixed_stretch) {
		VERTEX.y -= hop_height * max(sin(phase * TAU), 0.0);
	}
}

void fragment() {
	COLOR = texture(TEXTURE, UV) * tint;
}
