shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform vec4 near_color : source_color = vec4(0.62, 0.68, 0.75, 1.0);
uniform vec4 far_color : source_color = vec4(0.78, 0.82, 0.88, 1.0);
uniform vec4 sun_color : source_color = vec4(1.0, 0.85, 0.6, 1.0);
uniform float distance_density : hint_range(0.0, 1.0) = 0.08;
uniform float height_density : hint_range(0.0, 2.0) = 0.6;
uniform float height_falloff : hint_range(0.01, 4.0) = 1.2;
uniform float fog_base_height : hint_range(-50.0, 50.0) = -0.5;
uniform float color_distance : hint_range(1.0, 200.0) = 25.0;
uniform float sun_azimuth_degrees : hint_range(-180.0, 180.0) = 20.0;
uniform float sun_elevation_degrees : hint_range(-10.0, 90.0) = 15.0;
uniform float sun_glow : hint_range(0.0, 2.0) = 0.6;
uniform float max_opacity : hint_range(0.0, 1.0) = 1.0;

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
	vec3 scene = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 view_position = scene_view_position(SCREEN_UV, INV_PROJECTION_MATRIX);
	float distance_to_point = length(view_position);
	vec3 world = (INV_VIEW_MATRIX * vec4(view_position, 1.0)).xyz;
	vec3 camera_world = INV_VIEW_MATRIX[3].xyz;
	vec3 ray = (world - camera_world) / max(distance_to_point, 1e-4);
	float distance_fog = 1.0 - exp(-distance_density * distance_to_point);
	float h0 = camera_world.y - fog_base_height;
	float rise = ray.y * distance_to_point;
	float integral = abs(rise) > 1e-3
		? exp(-height_falloff * h0) * (1.0 - exp(-height_falloff * rise)) / (height_falloff * rise)
		: exp(-height_falloff * h0);
	float height_fog = 1.0 - exp(-height_density * distance_to_point * integral);
	float fog = clamp(max(distance_fog, height_fog), 0.0, max_opacity);
	vec3 fog_color = mix(near_color.rgb, far_color.rgb, smoothstep(0.0, color_distance, distance_to_point));
	float azimuth = radians(sun_azimuth_degrees);
	float elevation = radians(sun_elevation_degrees);
	vec3 sun_direction = vec3(sin(azimuth) * cos(elevation), sin(elevation), -cos(azimuth) * cos(elevation));
	float toward_sun = pow(clamp(dot(ray, sun_direction), 0.0, 1.0), 24.0);
	fog_color += sun_color.rgb * toward_sun * sun_glow;
	ALBEDO = mix(scene, fog_color, fog);
}
