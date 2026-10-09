shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_texture : hint_depth_texture, filter_nearest;
uniform float sun_azimuth_degrees : hint_range(-180.0, 180.0) = 8.0;
uniform float sun_elevation_degrees : hint_range(-10.0, 90.0) = 9.0;
uniform vec4 ray_color : source_color = vec4(1.0, 0.86, 0.6, 1.0);
uniform int samples : hint_range(8, 96) = 48;
uniform float density : hint_range(0.1, 1.0) = 0.85;
uniform float decay : hint_range(0.8, 1.0) = 0.965;
uniform float exposure : hint_range(0.0, 2.0) = 0.5;
uniform float sky_depth : hint_range(10.0, 4000.0) = 50.0;
uniform float sun_size : hint_range(0.01, 1.0) = 0.25;
uniform float sun_glow : hint_range(0.0, 2.0) = 0.6;

varying vec2 sun_uv;
varying float sun_visible;

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
	float azimuth = radians(sun_azimuth_degrees);
	float elevation = radians(sun_elevation_degrees);
	vec3 direction = vec3(sin(azimuth) * cos(elevation), sin(elevation), -cos(azimuth) * cos(elevation));
	vec4 clip = PROJECTION_MATRIX * vec4((VIEW_MATRIX * vec4(direction, 0.0)).xyz, 0.0);
	sun_visible = step(0.0, clip.w);
	sun_uv = clip.xy / max(clip.w, 1e-4) * 0.5 + 0.5;
}

float source(vec2 uv, mat4 inv_projection, float aspect) {
	float depth = -scene_view_position(uv, inv_projection).z;
	float sky = step(sky_depth, depth);
	vec2 offset = (uv - sun_uv) * vec2(aspect, 1.0);
	return sky * exp(-dot(offset, offset) / (sun_size * sun_size));
}

void fragment() {
	vec3 scene = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	float aspect = VIEWPORT_SIZE.x / VIEWPORT_SIZE.y;
	vec2 step_uv = (SCREEN_UV - sun_uv) * density / float(samples);
	vec2 uv = SCREEN_UV;
	float illumination = 1.0;
	float total = 0.0;
	for (int i = 0; i < samples; i++) {
		uv -= step_uv;
		total += source(uv, INV_PROJECTION_MATRIX, aspect) * illumination;
		illumination *= decay;
	}
	float shafts = total / float(samples) * exposure * sun_visible;
	float glow = source(SCREEN_UV, INV_PROJECTION_MATRIX, aspect) * sun_glow * sun_visible;
	ALBEDO = scene + ray_color.rgb * (shafts * 4.0 + glow);
}
