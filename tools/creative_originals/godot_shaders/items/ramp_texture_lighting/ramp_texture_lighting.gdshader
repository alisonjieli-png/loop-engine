shader_type spatial;

uniform sampler2D light_ramp : source_color, filter_linear, repeat_disable;
uniform vec4 albedo : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float ramp_offset : hint_range(-0.5, 0.5) = 0.0;
uniform float specular_size : hint_range(0.0, 1.0) = 0.12;
uniform float specular_strength : hint_range(0.0, 2.0) = 0.6;
uniform float rim_amount : hint_range(0.0, 1.0) = 0.3;
uniform float rim_width : hint_range(0.0, 1.0) = 0.25;

void fragment() {
	ALBEDO = albedo.rgb;
}

void light() {
	float half_lambert = clamp(dot(NORMAL, LIGHT) * 0.5 + 0.5, 0.0, 1.0) * ATTENUATION;
	vec3 ramp = texture(light_ramp, vec2(clamp(half_lambert + ramp_offset, 0.01, 0.99), 0.5)).rgb;
	DIFFUSE_LIGHT += ramp * LIGHT_COLOR / PI;
	vec3 halfway = normalize(LIGHT + VIEW);
	float highlight = step(1.0 - specular_size * 0.2, dot(NORMAL, halfway)) * ATTENUATION;
	SPECULAR_LIGHT += highlight * specular_strength * texture(light_ramp, vec2(0.99, 0.5)).rgb * LIGHT_COLOR / PI;
	float rim = smoothstep(1.0 - rim_width, 1.0, 1.0 - dot(NORMAL, VIEW)) * half_lambert;
	SPECULAR_LIGHT += rim * rim_amount * ramp * LIGHT_COLOR / PI;
}
