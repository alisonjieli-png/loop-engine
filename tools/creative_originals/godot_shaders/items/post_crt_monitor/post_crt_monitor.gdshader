shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float curvature : hint_range(0.0, 0.5) = 0.12;
uniform float scanline_pixels : hint_range(2.0, 12.0) = 3.0;
uniform float scanline_strength : hint_range(0.0, 1.0) = 0.45;
uniform float mask_strength : hint_range(0.0, 1.0) = 0.3;
uniform float mask_pixels : hint_range(1.0, 6.0) = 1.0;
uniform float glow : hint_range(0.0, 1.0) = 0.25;
uniform float vignette : hint_range(0.0, 2.0) = 0.6;
uniform float corner_radius : hint_range(0.0, 0.2) = 0.04;
uniform float brightness : hint_range(0.5, 2.0) = 1.2;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 centered = SCREEN_UV * 2.0 - 1.0;
	centered *= 1.0 + curvature * dot(centered, centered) * vec2(0.5, 0.65);
	vec2 uv = centered * 0.5 + 0.5;
	vec2 outside = step(vec2(0.0), uv) * step(uv, vec2(1.0));
	vec2 corner = max(abs(centered) - (1.0 - corner_radius), 0.0);
	float rounded = 1.0 - smoothstep(corner_radius * 0.8, corner_radius, length(corner));
	vec3 color = textureLod(screen_texture, uv, 0.0).rgb;
	color += textureLod(screen_texture, uv, 3.0).rgb * glow;
	float line = 0.5 + 0.5 * cos(uv.y * VIEWPORT_SIZE.y / scanline_pixels * TAU);
	color *= mix(1.0, line * 0.7 + 0.3, scanline_strength);
	float column = mod(floor(FRAGCOORD.x / mask_pixels), 3.0);
	vec3 mask = vec3(column < 0.5 ? 1.0 : 0.0, column >= 0.5 && column < 1.5 ? 1.0 : 0.0, column >= 1.5 ? 1.0 : 0.0);
	color *= mix(vec3(1.0), mask * 1.6 + 0.2, mask_strength);
	float edge = 1.0 - dot(centered * 0.5, centered * 0.5) * vignette;
	ALBEDO = color * edge * brightness * outside.x * outside.y * rounded;
}
