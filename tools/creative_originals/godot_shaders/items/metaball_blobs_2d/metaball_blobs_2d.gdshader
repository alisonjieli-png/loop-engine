shader_type canvas_item;

uniform vec4 blob_color : source_color = vec4(1.0, 0.35, 0.25, 1.0);
uniform vec4 highlight_color : source_color = vec4(1.0, 0.85, 0.45, 1.0);
uniform vec4 background_top : source_color = vec4(0.2, 0.05, 0.3, 1.0);
uniform vec4 background_bottom : source_color = vec4(0.45, 0.08, 0.25, 1.0);
uniform int blob_count : hint_range(1, 12) = 7;
uniform float blob_size : hint_range(0.01, 0.2) = 0.06;
uniform float threshold : hint_range(0.5, 4.0) = 1.0;
uniform float speed : hint_range(0.0, 3.0) = 0.4;
uniform float rim_glow : hint_range(0.0, 2.0) = 0.6;

float field(vec2 p) {
	float total = 0.0;
	for (int i = 0; i < blob_count; i++) {
		float fi = float(i);
		vec2 center = vec2(0.5 + 0.32 * sin(TIME * speed * (0.6 + fi * 0.13) + fi * 1.7),
						   0.5 + 0.38 * cos(TIME * speed * (0.5 + fi * 0.11) + fi * 2.3));
		vec2 delta = p - center;
		total += blob_size * blob_size / max(dot(delta, delta), 1e-5);
	}
	return total;
}

void fragment() {
	float f = field(UV);
	float e = 0.004;
	vec2 gradient = vec2(field(UV + vec2(e, 0.0)) - f, field(UV + vec2(0.0, e)) - f) / e;
	float inside = smoothstep(threshold * 0.95, threshold * 1.05, f);
	vec3 normal = normalize(vec3(-gradient * 0.004, 1.0));
	float light = clamp(dot(normal, normalize(vec3(-0.4, -0.6, 0.7))), 0.0, 1.0);
	vec3 blob = mix(blob_color.rgb * 0.7, highlight_color.rgb, pow(light, 3.0));
	vec3 background = mix(background_top.rgb, background_bottom.rgb, UV.y);
	float rim = smoothstep(threshold * 0.5, threshold, f) * (1.0 - inside);
	vec3 color = mix(background + blob_color.rgb * rim * rim_glow, blob, inside);
	COLOR = vec4(color, 1.0);
}
