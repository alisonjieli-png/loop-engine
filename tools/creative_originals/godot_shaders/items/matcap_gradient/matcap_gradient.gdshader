shader_type spatial;
render_mode unshaded;

uniform sampler2D matcap : source_color, hint_default_white, filter_linear;
uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float rim_strength : hint_range(0.0, 2.0) = 0.25;
uniform vec4 rim_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float cavity_strength : hint_range(0.0, 1.0) = 0.3;

void fragment() {
	vec3 n = normalize(NORMAL);
	vec3 view_direction = normalize(-VERTEX);
	vec3 reflected = reflect(-view_direction, n);
	vec3 r = reflected + vec3(0.0, 0.0, 1.0);
	vec2 lookup = r.xy / (2.0 * length(r)) + 0.5;
	lookup.y = 1.0 - lookup.y;
	vec3 shade = texture(matcap, lookup).rgb * tint.rgb;
	float facing = clamp(dot(n, view_direction), 0.0, 1.0);
	shade += rim_color.rgb * pow(1.0 - facing, 3.0) * rim_strength;
	float cavity = clamp(length(fwidth(n)) * 4.0, 0.0, 1.0) * cavity_strength;
	ALBEDO = shade * (1.0 - cavity);
}
