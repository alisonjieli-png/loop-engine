shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.32, 0.55, 0.85, 1.0);
uniform vec4 shadow_tint : source_color = vec4(0.18, 0.16, 0.36, 1.0);
uniform int bands : hint_range(1, 8) = 3;
uniform float band_softness : hint_range(0.0, 0.3) = 0.04;
uniform vec4 rim_color : source_color = vec4(1.0, 0.93, 0.78, 1.0);
uniform float rim_width : hint_range(0.0, 1.0) = 0.32;
uniform float rim_strength : hint_range(0.0, 4.0) = 1.4;
uniform float rim_light_bias : hint_range(0.0, 1.0) = 0.65;

void fragment() {
	ALBEDO = base_color.rgb;
}

void light() {
	// Half-Lambert keeps the dark side readable before it is cut into bands.
	float lit = clamp(dot(NORMAL, LIGHT) * 0.5 + 0.5, 0.0, 1.0) * ATTENUATION;
	float steps = float(bands);
	float scaled = lit * steps;
	float soft = max(band_softness * steps, 0.0001);
	float quantized = (floor(scaled) + smoothstep(1.0 - soft, 1.0, fract(scaled))) / steps;
	vec3 band_light = mix(shadow_tint.rgb, vec3(1.0), clamp(quantized, 0.0, 1.0));
	DIFFUSE_LIGHT += band_light * LIGHT_COLOR / PI;

	float facing = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float rim = smoothstep(1.0 - rim_width, 1.0 - rim_width + 0.04, facing);
	rim *= mix(1.0, smoothstep(0.35, 0.65, lit), rim_light_bias);
	SPECULAR_LIGHT += rim * rim_strength * rim_color.rgb * LIGHT_COLOR / PI;
}
