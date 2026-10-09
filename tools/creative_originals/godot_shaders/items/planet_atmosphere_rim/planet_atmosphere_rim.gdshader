shader_type spatial;
render_mode blend_add, cull_back, depth_draw_never, shadows_disabled;

uniform vec4 atmosphere_color : source_color = vec4(0.35, 0.6, 1.0, 1.0);
uniform vec4 sunset_color : source_color = vec4(1.0, 0.5, 0.3, 1.0);
uniform float shell_radius : hint_range(0.1, 10.0) = 1.0;
uniform float planet_radius : hint_range(0.1, 10.0) = 0.9;
uniform float density : hint_range(0.0, 10.0) = 1.2;
uniform float brightness : hint_range(0.0, 8.0) = 1.6;
uniform float terminator_softness : hint_range(0.0, 1.0) = 0.35;
uniform float night_glow : hint_range(0.0, 0.5) = 0.02;

varying vec3 closest_normal;
varying float scattering;

void fragment() {
	vec3 camera_object = (inverse(MODEL_MATRIX) * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
	vec3 point_object = (inverse(MODEL_MATRIX) * INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 ray = normalize(point_object - camera_object);
	float along = -dot(camera_object, ray);
	vec3 closest = camera_object + ray * along;
	float impact = length(closest);
	float half_shell = sqrt(max(shell_radius * shell_radius - impact * impact, 0.0));
	float path = 2.0 * half_shell;
	vec3 lit_point = closest;
	if (impact < planet_radius) {
		float half_planet = sqrt(max(planet_radius * planet_radius - impact * impact, 0.0));
		path = half_shell - half_planet;
		lit_point = camera_object + ray * (along - half_planet);
	}
	float grazing_chord = 2.0 * sqrt(max(shell_radius * shell_radius - planet_radius * planet_radius, 1e-4));
	float depth = path / grazing_chord;
	scattering = 1.0 - exp(-density * depth);
	closest_normal = (VIEW_MATRIX * MODEL_MATRIX * vec4(normalize(lit_point + 1e-5), 0.0)).xyz;
	ALBEDO = vec3(0.0);
	EMISSION = atmosphere_color.rgb * scattering * night_glow;
}

void light() {
	vec3 n = normalize(closest_normal);
	float sun_side = smoothstep(-terminator_softness, terminator_softness, dot(n, LIGHT));
	float edge = 1.0 - smoothstep(0.0, terminator_softness + 0.2, abs(dot(n, LIGHT)));
	vec3 tint = mix(atmosphere_color.rgb, sunset_color.rgb, edge * 0.7);
	SPECULAR_LIGHT += tint * scattering * sun_side * brightness * LIGHT_COLOR / PI;
}
