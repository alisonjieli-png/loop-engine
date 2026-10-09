shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float strength : hint_range(0.0, 0.05) = 0.012;
uniform float falloff_power : hint_range(0.5, 4.0) = 2.0;
uniform int samples : hint_range(1, 16) = 6;
uniform float center_x : hint_range(0.0, 1.0) = 0.5;
uniform float center_y : hint_range(0.0, 1.0) = 0.5;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 center = vec2(center_x, center_y);
	vec2 offset = SCREEN_UV - center;
	float amount = pow(length(offset) * 1.4142, falloff_power) * strength;
	vec2 direction = normalize(offset + vec2(1e-6));
	vec3 total = vec3(0.0);
	for (int i = 0; i < samples; i++) {
		float t = samples > 1 ? float(i) / float(samples - 1) : 1.0;
		vec2 shift = direction * amount * t;
		total.r += textureLod(screen_texture, SCREEN_UV + shift, 0.0).r;
		total.g += textureLod(screen_texture, SCREEN_UV, 0.0).g;
		total.b += textureLod(screen_texture, SCREEN_UV - shift, 0.0).b;
	}
	ALBEDO = total / float(samples);
}
