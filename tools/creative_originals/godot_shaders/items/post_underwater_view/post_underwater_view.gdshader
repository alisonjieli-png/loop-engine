shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 water_color : source_color = vec4(0.04, 0.28, 0.38, 1.0);
uniform float absorption : hint_range(0.0, 2.0) = 0.22;
uniform float red_absorption : hint_range(1.0, 6.0) = 3.0;
uniform float distortion : hint_range(0.0, 0.03) = 0.006;
uniform float wave_frequency : hint_range(1.0, 60.0) = 18.0;
uniform float wave_speed : hint_range(0.0, 6.0) = 1.5;
uniform float surface_light : hint_range(0.0, 1.0) = 0.35;
uniform float vignette : hint_range(0.0, 1.0) = 0.45;

// View-space position of the opaque scene at a screen position.
vec3 scene_view_position(vec2 screen_uv, mat4 inv_projection) {
	float raw = texture(depth_texture, screen_uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw * 2.0 - 1.0);
#else
	vec3 ndc = vec3(screen_uv * 2.0 - 1.0, raw);
#endif
	vec4 view = inv_projection * vec4(ndc, 1.0);
	return view.xyz / view.w;
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec2 wobble = vec2(sin(SCREEN_UV.y * wave_frequency + TIME * wave_speed),
					   cos(SCREEN_UV.x * wave_frequency * 0.8 + TIME * wave_speed * 1.3)) * distortion;
	vec2 uv = SCREEN_UV + wobble;
	vec3 scene = textureLod(screen_texture, uv, 0.0).rgb;
	float distance_to_point = min(length(scene_view_position(uv, INV_PROJECTION_MATRIX)), 200.0);
	vec3 coefficients = absorption * vec3(red_absorption, 1.0, 0.7);
	vec3 transmittance = exp(-coefficients * distance_to_point);
	float scatter = 1.0 - exp(-absorption * distance_to_point);
	vec3 color = scene * transmittance + water_color.rgb * scatter;
	color += water_color.rgb * surface_light * (1.0 - SCREEN_UV.y) * (1.0 - SCREEN_UV.y);
	float edge = length(SCREEN_UV - 0.5) * 1.4;
	ALBEDO = color * (1.0 - vignette * edge * edge);
}
