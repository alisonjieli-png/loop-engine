shader_type canvas_item;

uniform float hue_shift_degrees : hint_range(-180.0, 180.0) = 0.0;
uniform float saturation : hint_range(0.0, 3.0) = 1.0;
uniform float value : hint_range(0.0, 3.0) = 1.0;
uniform float contrast : hint_range(0.0, 3.0) = 1.0;
uniform float grayscale : hint_range(0.0, 1.0) = 0.0;
uniform float sepia : hint_range(0.0, 1.0) = 0.0;

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

vec3 rgb_to_hsv(vec3 c) {
	float high = max(max(c.r, c.g), c.b);
	float low = min(min(c.r, c.g), c.b);
	float delta = high - low;
	float hue = 0.0;
	if (delta > 1e-5) {
		if (high == c.r) {
			hue = mod((c.g - c.b) / delta, 6.0);
		} else if (high == c.g) {
			hue = (c.b - c.r) / delta + 2.0;
		} else {
			hue = (c.r - c.g) / delta + 4.0;
		}
	}
	return vec3(hue / 6.0, high > 1e-5 ? delta / high : 0.0, high);
}

vec3 hsv_to_rgb(vec3 c) {
	vec3 k = clamp(abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
	return c.z * mix(vec3(1.0), k, c.y);
}

void fragment() {
	vec4 source = texture(TEXTURE, UV);
	vec3 hsv = rgb_to_hsv(source.rgb);
	hsv.x = fract(hsv.x + hue_shift_degrees / 360.0);
	hsv.y = clamp(hsv.y * saturation, 0.0, 1.0);
	hsv.z *= value;
	vec3 color = hsv_to_rgb(hsv);
	color = (color - 0.5) * contrast + 0.5;
	float l = dot(color, vec3(0.299, 0.587, 0.114));
	color = mix(color, vec3(l), grayscale);
	vec3 toned = vec3(l * 1.07, l * 0.88, l * 0.66) + vec3(0.08, 0.04, 0.0);
	color = mix(color, toned, sepia);
	COLOR = vec4(clamp(color, 0.0, 1.0), source.a) * tint;
}
