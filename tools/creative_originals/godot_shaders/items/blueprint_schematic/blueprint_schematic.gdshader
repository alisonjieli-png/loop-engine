shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 fill_color : source_color = vec4(0.08, 0.26, 0.58, 0.25);
uniform vec4 line_color : source_color = vec4(0.9, 0.96, 1.0, 1.0);
uniform float contour_width : hint_range(0.0, 0.6) = 0.25;
uniform float dash_pixels : hint_range(2.0, 40.0) = 10.0;
uniform float hidden_opacity : hint_range(0.0, 1.0) = 0.55;
uniform float grid_size : hint_range(0.01, 1.0) = 0.1;
uniform float grid_opacity : hint_range(0.0, 1.0) = 0.25;

varying vec3 object_position;

void vertex() {
	object_position = VERTEX;
}

void fragment() {
	float facing = abs(dot(NORMAL, VIEW));
	float contour = 1.0 - smoothstep(contour_width * 0.5, contour_width, facing);
	float grid = 0.0;
	vec3 coordinate = object_position / grid_size;
	vec3 width = max(fwidth(coordinate), vec3(1e-5));
	vec3 distance_pixels = abs(fract(coordinate - 0.5) - 0.5) / width;
	float nearest = min(min(distance_pixels.x, distance_pixels.y), distance_pixels.z);
	grid = 1.0 - clamp(nearest - 0.5, 0.0, 1.0);
	float line = contour;
	float opacity = 1.0;
	if (!FRONT_FACING) {
		float dash = step(0.5, fract((FRAGCOORD.x + FRAGCOORD.y) / (dash_pixels * 2.0)));
		line *= dash;
		opacity = hidden_opacity;
		grid = 0.0;
	}
	float ink = max(line * opacity, grid * grid_opacity);
	ALBEDO = mix(fill_color.rgb, line_color.rgb, ink);
	ALPHA = max(fill_color.a, ink);
}
