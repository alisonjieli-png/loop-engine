shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform int mode : hint_range(0, 3) = 1;
uniform float severity : hint_range(0.0, 1.0) = 1.0;
uniform bool split_view = false;

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

vec3 to_srgb(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 linear_color = to_linear(color);
	mat3 simulation;
	if (mode == 0) {
		simulation = mat3(vec3(0.152286, 0.114503, -0.003882), vec3(1.052583, 0.786281, -0.048116),
						  vec3(-0.204868, 0.099216, 1.051998));
	} else if (mode == 1) {
		simulation = mat3(vec3(0.367322, 0.280085, -0.011820), vec3(0.860646, 0.672501, 0.042940),
						  vec3(-0.227968, 0.047413, 0.968881));
	} else if (mode == 2) {
		simulation = mat3(vec3(1.255528, -0.078411, 0.004733), vec3(-0.076749, 0.930809, 0.691367),
						  vec3(-0.178779, 0.147602, 0.303900));
	} else {
		float l = dot(linear_color, vec3(0.2126, 0.7152, 0.0722));
		simulation = mat3(vec3(0.2126), vec3(0.7152), vec3(0.0722));
	}
	vec3 simulated = clamp(simulation * linear_color, 0.0, 1.0);
	vec3 result = to_srgb(mix(linear_color, simulated, severity));
	if (split_view && SCREEN_UV.x < 0.5) {
		result = color;
	}
	ALBEDO = result;
}
