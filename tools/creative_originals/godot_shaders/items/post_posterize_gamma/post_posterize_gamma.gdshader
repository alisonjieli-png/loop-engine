shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform int levels : hint_range(2, 32) = 5;
uniform float gamma : hint_range(0.3, 3.0) = 1.0;
uniform bool luminance_only = false;
uniform float edge_softness : hint_range(0.0, 0.5) = 0.0;
uniform float saturation : hint_range(0.0, 2.0) = 1.15;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float quantize(float value, float steps) {
	float scaled = pow(clamp(value, 0.0, 1.0), 1.0 / gamma) * steps;
	float lower = floor(scaled);
	float blend = smoothstep(0.5 - edge_softness, 0.5 + edge_softness, fract(scaled));
	float stepped = (lower + (edge_softness > 0.0 ? blend : step(0.5, fract(scaled)))) / steps;
	return pow(stepped, gamma);
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	float l = luminance(color);
	color = mix(vec3(l), color, saturation);
	float steps = float(levels - 1);
	vec3 result;
	if (luminance_only) {
		float q = quantize(l, steps);
		result = color * (q / max(l, 1e-4));
	} else {
		result = vec3(quantize(color.r, steps), quantize(color.g, steps), quantize(color.b, steps));
	}
	ALBEDO = clamp(result, 0.0, 1.0);
}
