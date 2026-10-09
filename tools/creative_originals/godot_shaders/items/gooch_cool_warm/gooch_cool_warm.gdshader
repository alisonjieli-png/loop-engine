shader_type spatial;

uniform vec4 surface_color : source_color = vec4(0.72, 0.66, 0.58, 1.0);
uniform vec4 cool_color : source_color = vec4(0.08, 0.16, 0.55, 1.0);
uniform vec4 warm_color : source_color = vec4(0.62, 0.48, 0.08, 1.0);
uniform float cool_mix : hint_range(0.0, 1.0) = 0.25;
uniform float warm_mix : hint_range(0.0, 1.0) = 0.5;
uniform float highlight_strength : hint_range(0.0, 2.0) = 0.7;
uniform float shininess : hint_range(1.0, 256.0) = 48.0;
uniform float edge_darkening : hint_range(0.0, 1.0) = 0.7;
uniform float edge_width : hint_range(0.0, 0.6) = 0.22;

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float edge = smoothstep(edge_width, edge_width * 0.5, facing);
	ALBEDO = vec3(1.0 - edge_darkening * edge);
}

void light() {
	float t = clamp((1.0 + dot(NORMAL, LIGHT)) * 0.5, 0.0, 1.0);
	vec3 cool = cool_color.rgb + cool_mix * surface_color.rgb;
	vec3 warm = warm_color.rgb + warm_mix * surface_color.rgb;
	DIFFUSE_LIGHT += mix(cool, warm, t) * LIGHT_COLOR / PI;
	vec3 halfway = normalize(LIGHT + VIEW);
	float highlight = pow(clamp(dot(NORMAL, halfway), 0.0, 1.0), shininess);
	SPECULAR_LIGHT += highlight * highlight_strength * ATTENUATION * LIGHT_COLOR / PI;
}
