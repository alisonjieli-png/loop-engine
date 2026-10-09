shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform vec4 vignette_color : source_color = vec4(0.02, 0.0, 0.04, 1.0);
uniform float intensity : hint_range(0.0, 1.0) = 0.75;
uniform float radius : hint_range(0.0, 1.5) = 0.55;
uniform float softness : hint_range(0.01, 1.0) = 0.45;
uniform float roundness : hint_range(0.0, 1.0) = 1.0;
uniform float focus_x : hint_range(0.0, 1.0) = 0.5;
uniform float focus_y : hint_range(0.0, 1.0) = 0.5;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec2 offset = SCREEN_UV - vec2(focus_x, focus_y);
	float aspect = VIEWPORT_SIZE.x / VIEWPORT_SIZE.y;
	offset.x *= mix(1.0, aspect, roundness);
	vec2 shaped = abs(offset) * 2.0;
	float round_distance = length(shaped);
	float box_distance = max(shaped.x, shaped.y);
	float distance_to_focus = mix(box_distance, round_distance, roundness);
	float mask = smoothstep(radius, radius + softness, distance_to_focus);
	ALBEDO = mix(color, vignette_color.rgb, mask * intensity);
}
