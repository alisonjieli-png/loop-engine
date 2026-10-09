shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.85, 0.55, 0.25, 1.0);
uniform vec4 stripe_color : source_color = vec4(0.3, 0.15, 0.08, 1.0);
uniform float twist_degrees_per_unit : hint_range(-720.0, 720.0) = 160.0;
uniform float pivot_height : hint_range(-5.0, 5.0) = -0.6;
uniform float wobble_degrees : hint_range(0.0, 180.0) = 30.0;
uniform float wobble_speed : hint_range(0.0, 10.0) = 1.5;
uniform float stripes : hint_range(0.0, 20.0) = 6.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.5;

varying vec3 rest_position;

mat2 rotation(float angle) {
	return mat2(vec2(cos(angle), sin(angle)), vec2(-sin(angle), cos(angle)));
}

void vertex() {
	rest_position = VERTEX;
	float height = VERTEX.y - pivot_height;
	float angle = radians(twist_degrees_per_unit * height + wobble_degrees * sin(TIME * wobble_speed) * height);
	mat2 turn = rotation(angle);
	VERTEX.xz = turn * VERTEX.xz;
	NORMAL.xz = turn * NORMAL.xz;
	TANGENT.xz = turn * TANGENT.xz;
}

void fragment() {
	float stripe = step(0.5, fract(rest_position.x * stripes * 0.5 + 0.25));
	ALBEDO = mix(albedo.rgb, stripe_color.rgb, stripe);
	ROUGHNESS = roughness;
}
