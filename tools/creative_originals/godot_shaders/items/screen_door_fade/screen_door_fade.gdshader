shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.55, 0.6, 0.68, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.7;
uniform float fade : hint_range(0.0, 1.0) = 1.0;
uniform float near_distance : hint_range(0.0, 20.0) = 1.0;
uniform float far_distance : hint_range(0.1, 40.0) = 2.6;
uniform float dither_scale : hint_range(1.0, 8.0) = 1.0;
uniform bool use_distance = true;

float bayer4(vec2 pixel) {
	ivec2 p = ivec2(mod(floor(pixel), 4.0));
	int index = p.x + p.y * 4;
	int values[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	return (float(values[index]) + 0.5) / 16.0;
}

void fragment() {
	float opacity = fade;
	if (use_distance) {
		opacity *= smoothstep(near_distance, far_distance, length(VERTEX));
	}
	if (opacity < bayer4(FRAGCOORD.xy / dither_scale)) {
		discard;
	}
	ALBEDO = albedo.rgb;
	ROUGHNESS = roughness;
}
