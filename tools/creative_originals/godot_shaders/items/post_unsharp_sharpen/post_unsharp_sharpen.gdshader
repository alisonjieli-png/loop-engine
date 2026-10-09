shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_nearest;
uniform float amount : hint_range(0.0, 3.0) = 1.2;
uniform float radius_pixels : hint_range(0.5, 4.0) = 1.0;
uniform float threshold : hint_range(0.0, 0.2) = 0.01;
uniform bool luminance_only = true;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 texel = radius_pixels / VIEWPORT_SIZE;
	vec3 center = texture(screen_texture, SCREEN_UV).rgb;
	vec3 blur = center * 4.0;
	blur += texture(screen_texture, SCREEN_UV + vec2(texel.x, 0.0)).rgb * 2.0;
	blur += texture(screen_texture, SCREEN_UV - vec2(texel.x, 0.0)).rgb * 2.0;
	blur += texture(screen_texture, SCREEN_UV + vec2(0.0, texel.y)).rgb * 2.0;
	blur += texture(screen_texture, SCREEN_UV - vec2(0.0, texel.y)).rgb * 2.0;
	blur += texture(screen_texture, SCREEN_UV + texel).rgb;
	blur += texture(screen_texture, SCREEN_UV - texel).rgb;
	blur += texture(screen_texture, SCREEN_UV + vec2(texel.x, -texel.y)).rgb;
	blur += texture(screen_texture, SCREEN_UV + vec2(-texel.x, texel.y)).rgb;
	blur /= 16.0;
	vec3 detail = center - blur;
	if (luminance_only) {
		detail = vec3(luminance(detail));
	}
	float strength = smoothstep(threshold, threshold * 2.0 + 1e-4, abs(luminance(center - blur)));
	ALBEDO = clamp(center + detail * amount * strength, 0.0, 1.0);
}
