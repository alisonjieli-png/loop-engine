shader_type canvas_item;

uniform vec4 fill_color : source_color = vec4(0.95, 0.45, 0.55, 1.0);
uniform vec4 outline_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 glow_color : source_color = vec4(1.0, 0.5, 0.7, 1.0);
uniform vec4 background_color : source_color = vec4(0.1, 0.08, 0.16, 1.0);
uniform float morph_speed : hint_range(0.0, 3.0) = 0.4;
uniform float shape_index : hint_range(0.0, 4.0) = 2.5;
uniform bool animate = true;
uniform float size : hint_range(0.05, 0.5) = 0.3;
uniform float outline_width : hint_range(0.0, 0.05) = 0.012;
uniform float glow_width : hint_range(0.0, 0.3) = 0.08;
uniform bool show_contours = false;

float circle_sdf(vec2 p, float r) {
	return length(p) - r;
}

float box_sdf(vec2 p, vec2 half_size, float corner) {
	vec2 q = abs(p) - half_size + corner;
	return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - corner;
}

float star_sdf(vec2 p, float r, float inner) {
	float angle = atan(p.y, p.x);
	float sector = TAU / 5.0;
	float a = mod(angle + sector * 0.5, sector) - sector * 0.5;
	float radius = mix(r * inner, r, pow(abs(cos(a * 2.5)), 1.5));
	return (length(p) - radius) * 0.7;
}

float heart_sdf(vec2 p, float r) {
	p.y = -p.y + r * 0.35;
	p /= r;
	float a = atan(p.x, p.y) / PI;
	float shape_radius = 0.75 * (abs(a) * (13.0 - 22.0 * abs(a) + 10.0 * a * a) / (6.0 - 5.0 * abs(a)));
	return (length(p) - shape_radius) * r * 0.5;
}

float shape_at(vec2 p, float index) {
	float i = mod(index, 4.0);
	if (i < 1.0) {
		return circle_sdf(p, size);
	} else if (i < 2.0) {
		return box_sdf(p, vec2(size * 0.85), size * 0.25);
	} else if (i < 3.0) {
		return star_sdf(p, size * 1.15, 0.5);
	}
	return heart_sdf(p, size * 1.2);
}

void fragment() {
	vec2 p = UV - 0.5;
	float t = animate ? TIME * morph_speed : shape_index;
	float a = floor(t);
	float blend = smoothstep(0.2, 0.8, fract(t));
	float d = mix(shape_at(p, a), shape_at(p, a + 1.0), blend);
	float width = fwidth(d);
	float fill = 1.0 - smoothstep(-width, width, d);
	float outline = 1.0 - smoothstep(outline_width - width, outline_width + width, abs(d));
	float glow = exp(-max(d, 0.0) / max(glow_width, 1e-4) * 3.0) * (1.0 - fill);
	vec3 color = background_color.rgb + glow_color.rgb * glow * 0.6;
	if (show_contours) {
		color *= 0.8 + 0.2 * step(0.5, fract(d * 40.0));
	}
	color = mix(color, fill_color.rgb, fill);
	color = mix(color, outline_color.rgb, outline);
	COLOR = vec4(color, 1.0);
}
