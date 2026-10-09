shader_type canvas_item;

uniform vec4 flash_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;
uniform int mode : hint_range(0, 2) = 0;
uniform bool auto_blink = false;
uniform float blink_rate : hint_range(0.5, 30.0) = 12.0;
uniform float blink_duty : hint_range(0.0, 1.0) = 0.5;

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

void fragment() {
	vec4 source = texture(TEXTURE, UV) * tint;
	float amount = flash_amount;
	if (auto_blink) {
		amount *= step(fract(TIME * blink_rate), blink_duty);
	}
	vec3 color = source.rgb;
	if (mode == 0) {
		color = mix(source.rgb, flash_color.rgb, amount);
	} else if (mode == 1) {
		color = source.rgb + flash_color.rgb * amount;
	} else {
		color = mix(source.rgb, flash_color.rgb, step(0.001, amount));
	}
	COLOR = vec4(color, source.a);
}
