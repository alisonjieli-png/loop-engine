shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.88, 0.68, 0.58, 1.0);
uniform vec4 scatter_color : source_color = vec4(0.85, 0.2, 0.12, 1.0);
uniform float wrap : hint_range(0.0, 1.0) = 0.45;
uniform float scatter_width : hint_range(0.0, 1.0) = 0.35;
uniform float translucency : hint_range(0.0, 2.0) = 0.6;
uniform float translucency_power : hint_range(1.0, 16.0) = 4.0;
uniform float translucency_distortion : hint_range(0.0, 1.0) = 0.25;
uniform float specular_strength : hint_range(0.0, 1.0) = 0.25;
uniform float specular_power : hint_range(2.0, 128.0) = 24.0;

void fragment() {
	ALBEDO = albedo.rgb;
}

void light() {
	float n_dot_l = dot(NORMAL, LIGHT);
	float wrapped = clamp((n_dot_l + wrap) / (1.0 + wrap), 0.0, 1.0);
	float plain = clamp(n_dot_l, 0.0, 1.0);
	float band = clamp(wrapped - plain, 0.0, 1.0);
	vec3 scatter = scatter_color.rgb * band * smoothstep(0.0, scatter_width, band) * 2.0;
	DIFFUSE_LIGHT += (vec3(wrapped) + scatter) * ATTENUATION * LIGHT_COLOR / PI;
	vec3 through = normalize(LIGHT + NORMAL * translucency_distortion);
	float back = pow(clamp(dot(VIEW, -through), 0.0, 1.0), translucency_power) * translucency;
	DIFFUSE_LIGHT += scatter_color.rgb * back * LIGHT_COLOR / PI;
	vec3 halfway = normalize(LIGHT + VIEW);
	float specular = pow(clamp(dot(NORMAL, halfway), 0.0, 1.0), specular_power) * specular_strength;
	SPECULAR_LIGHT += specular * plain * ATTENUATION * LIGHT_COLOR / PI;
}
