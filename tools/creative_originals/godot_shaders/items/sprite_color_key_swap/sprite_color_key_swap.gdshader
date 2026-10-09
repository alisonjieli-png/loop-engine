shader_type canvas_item;

uniform vec4 key_1 : source_color = vec4(0.95, 0.6, 0.25, 1.0);
uniform vec4 target_1 : source_color = vec4(0.25, 0.8, 0.75, 1.0);
uniform vec4 key_2 : source_color = vec4(0.85, 0.35, 0.3, 1.0);
uniform vec4 target_2 : source_color = vec4(0.2, 0.45, 0.9, 1.0);
uniform vec4 key_3 : source_color = vec4(0.55, 0.2, 0.35, 1.0);
uniform vec4 target_3 : source_color = vec4(0.15, 0.15, 0.45, 1.0);
uniform float tolerance : hint_range(0.0, 1.0) = 0.16;
uniform float softness : hint_range(0.0, 0.5) = 0.1;
uniform bool keep_shading = true;

varying vec4 tint;

void vertex() {
	tint = COLOR;
}

float luma(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

vec3 swap(vec3 color, vec3 key, vec3 target) {
	float distance_to_key = distance(color, key);
	float weight = 1.0 - smoothstep(tolerance, tolerance + softness, distance_to_key);
	vec3 replacement = keep_shading ? target * (luma(color) / max(luma(key), 1e-3)) : target;
	return mix(color, clamp(replacement, 0.0, 1.0), weight);
}

void fragment() {
	vec4 source = texture(TEXTURE, UV);
	vec3 color = source.rgb;
	color = swap(color, key_1.rgb, target_1.rgb);
	color = swap(color, key_2.rgb, target_2.rgb);
	color = swap(color, key_3.rgb, target_3.rgb);
	COLOR = vec4(color, source.a) * tint;
}
