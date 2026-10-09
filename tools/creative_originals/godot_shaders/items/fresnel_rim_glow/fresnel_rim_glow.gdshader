shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.08, 0.1, 0.16, 1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.35;
uniform float metallic : hint_range(0.0, 1.0) = 0.2;
uniform vec4 glow_color : source_color = vec4(0.2, 0.85, 1.0, 1.0);
uniform float glow_power : hint_range(0.5, 8.0) = 2.5;
uniform float glow_intensity : hint_range(0.0, 8.0) = 3.0;
uniform float inner_glow : hint_range(0.0, 1.0) = 0.08;
uniform float pulse_speed : hint_range(0.0, 10.0) = 2.0;
uniform float pulse_depth : hint_range(0.0, 1.0) = 0.35;

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float fresnel = pow(1.0 - facing, glow_power);
	float pulse = 1.0 - pulse_depth * (0.5 + 0.5 * sin(TIME * pulse_speed));
	ALBEDO = base_color.rgb;
	ROUGHNESS = roughness;
	METALLIC = metallic;
	EMISSION = glow_color.rgb * (fresnel + inner_glow) * glow_intensity * pulse;
}
