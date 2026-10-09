shader_type spatial;
render_mode unshaded;

uniform float cells : hint_range(1.0, 64.0) = 8.0;
uniform vec4 dark_color : source_color = vec4(0.18, 0.18, 0.2, 1.0);
uniform vec4 light_color : source_color = vec4(0.82, 0.82, 0.85, 1.0);
uniform float direction_tint : hint_range(0.0, 1.0) = 0.45;
uniform float line_pixels : hint_range(0.0, 4.0) = 1.0;
uniform bool show_stretch = false;
uniform float stretch_range : hint_range(1.0, 8.0) = 3.0;

void fragment() {
	vec2 grid = UV * cells;
	vec2 cell = floor(grid);
	float checker = mod(cell.x + cell.y, 2.0);
	vec3 color = mix(dark_color.rgb, light_color.rgb, checker);
	vec3 ramps = vec3(fract(UV.x), fract(UV.y), 0.25);
	color = mix(color, color * (0.4 + 1.2 * ramps), direction_tint);
	vec2 local = fract(grid);
	float corner = step(local.x, 0.25) * step(local.y, 0.25) * step(0.05, local.x) * step(0.05, local.y);
	color = mix(color, vec3(1.0, 0.3, 0.2), corner * 0.8);
	vec2 width = max(fwidth(grid), vec2(1e-5));
	vec2 distance_pixels = abs(fract(grid - 0.5) - 0.5) / width;
	float line = 1.0 - clamp(min(distance_pixels.x, distance_pixels.y) - line_pixels * 0.5 + 0.5, 0.0, 1.0);
	color = mix(color, vec3(0.0), line * 0.6);
	if (show_stretch) {
		float du = length(vec2(dFdx(UV.x), dFdy(UV.x)));
		float dv = length(vec2(dFdx(UV.y), dFdy(UV.y)));
		float ratio = log2(max(du, 1e-6) / max(dv, 1e-6)) / log2(stretch_range);
		vec3 heat = ratio > 0.0 ? mix(vec3(0.2, 0.9, 0.3), vec3(1.0, 0.1, 0.1), clamp(ratio, 0.0, 1.0))
								: mix(vec3(0.2, 0.9, 0.3), vec3(0.1, 0.3, 1.0), clamp(-ratio, 0.0, 1.0));
		color = mix(color, heat, 0.6);
	}
	ALBEDO = color;
}
