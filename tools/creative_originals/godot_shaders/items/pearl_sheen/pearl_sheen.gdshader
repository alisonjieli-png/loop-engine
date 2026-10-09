shader_type spatial;

uniform vec4 body_color : source_color = vec4(0.93, 0.9, 0.86, 1.0);
uniform vec4 tint_a : source_color = vec4(1.0, 0.78, 0.86, 1.0);
uniform vec4 tint_b : source_color = vec4(0.78, 1.0, 0.88, 1.0);
uniform vec4 tint_c : source_color = vec4(1.0, 0.92, 0.7, 1.0);
uniform float orient_strength : hint_range(0.0, 1.0) = 0.55;
uniform float orient_bands : hint_range(0.5, 6.0) = 1.6;
uniform float satin_roughness : hint_range(0.0, 1.0) = 0.32;
uniform float inner_glow : hint_range(0.0, 1.0) = 0.12;
uniform vec4 rim_color : source_color = vec4(0.75, 0.85, 1.0, 1.0);
uniform float rim_strength : hint_range(0.0, 1.0) = 0.25;

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float phase = fract((1.0 - facing) * orient_bands + NORMAL.x * 0.15);
	vec3 orient = phase < 0.333 ? mix(tint_a.rgb, tint_b.rgb, phase * 3.0)
		: (phase < 0.666 ? mix(tint_b.rgb, tint_c.rgb, (phase - 0.333) * 3.0) : mix(tint_c.rgb, tint_a.rgb, (phase - 0.666) * 3.0));
	ALBEDO = mix(body_color.rgb, body_color.rgb * orient, orient_strength * (1.0 - facing * 0.4));
	ROUGHNESS = satin_roughness;
	METALLIC = 0.15;
	SPECULAR = 0.6;
	EMISSION = body_color.rgb * inner_glow * pow(facing, 2.0) + rim_color.rgb * pow(1.0 - facing, 4.0) * rim_strength;
}
