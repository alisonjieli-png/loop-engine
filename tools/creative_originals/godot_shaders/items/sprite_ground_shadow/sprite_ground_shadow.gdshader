shader_type canvas_item;

uniform vec4 shadow_color : source_color = vec4(0.05, 0.05, 0.1, 0.5);
uniform float flatten : hint_range(0.05, 1.5) = 0.45;
uniform float skew : hint_range(-3.0, 3.0) = 1.1;
uniform float base_v : hint_range(0.0, 1.0) = 1.0;
uniform float fade : hint_range(0.0, 1.0) = 0.6;
uniform float sway : hint_range(0.0, 1.0) = 0.0;

varying vec4 tint;

varying float distance_from_base;

void vertex() {
	tint = COLOR;
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 base = VERTEX - (UV - vec2(UV.x, base_v)) * size;
	float height = VERTEX.y - base.y;
	float lean = skew + sway * sin(TIME);
	VERTEX = vec2(VERTEX.x - height * flatten * lean, base.y - height * flatten);
	distance_from_base = abs(base_v - UV.y);
}

void fragment() {
	float alpha = texture(TEXTURE, UV).a;
	float strength = 1.0 - fade * distance_from_base;
	COLOR = vec4(shadow_color.rgb, alpha * shadow_color.a * strength * tint.a);
}
