shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 shield_color : source_color = vec4(0.25, 0.6, 1.0, 1.0);
uniform vec4 impact_color : source_color = vec4(1.0, 0.85, 0.5, 1.0);
uniform float hit_azimuth_degrees : hint_range(-180.0, 180.0) = 25.0;
uniform float hit_elevation_degrees : hint_range(-90.0, 90.0) = 15.0;
uniform float impact_progress : hint_range(0.0, 1.0) = 0.35;
uniform bool loop_impacts = true;
uniform float loop_period : hint_range(0.2, 5.0) = 1.5;
uniform float ring_width : hint_range(0.01, 0.5) = 0.12;
uniform float ring_reach_degrees : hint_range(10.0, 180.0) = 110.0;
uniform float base_strength : hint_range(0.0, 1.0) = 0.08;
uniform float rim_strength : hint_range(0.0, 2.0) = 0.6;

varying vec3 object_direction;

void vertex() {
	object_direction = normalize(VERTEX);
}

void fragment() {
	float azimuth = radians(hit_azimuth_degrees);
	float elevation = radians(hit_elevation_degrees);
	vec3 hit = vec3(sin(azimuth) * cos(elevation), sin(elevation), cos(azimuth) * cos(elevation));
	float progress = loop_impacts ? fract(TIME / loop_period) : impact_progress;
	float arc = acos(clamp(dot(normalize(object_direction), hit), -1.0, 1.0));
	float front = radians(ring_reach_degrees) * progress;
	float ring = 1.0 - smoothstep(0.0, ring_width, abs(arc - front));
	float energy = 1.0 - progress;
	float flash = (1.0 - smoothstep(0.0, 0.35, arc)) * (1.0 - smoothstep(0.0, 0.3, progress));
	float rim = pow(1.0 - abs(dot(NORMAL, VIEW)), 3.0) * rim_strength;
	vec3 color = shield_color.rgb * (base_strength + rim) + impact_color.rgb * (ring * energy * 1.5 + flash * 2.0);
	ALBEDO = color;
}
