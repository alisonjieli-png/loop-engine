shader_type spatial;

uniform sampler2D albedo_texture : source_color, hint_default_white, filter_nearest;
uniform vec4 color_a : source_color = vec4(0.85, 0.75, 0.55, 1.0);
uniform vec4 color_b : source_color = vec4(0.45, 0.25, 0.2, 1.0);
uniform float checker_cells : hint_range(1.0, 32.0) = 6.0;
uniform float snap_width : hint_range(40.0, 640.0) = 160.0;
uniform float snap_height : hint_range(30.0, 480.0) = 120.0;
uniform float affine_amount : hint_range(0.0, 1.0) = 1.0;
uniform float color_levels : hint_range(2.0, 64.0) = 32.0;
uniform float dither_amount : hint_range(0.0, 1.0) = 0.6;

varying vec3 affine_uv;

void vertex() {
	vec4 clip = PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	vec2 grid = vec2(snap_width, snap_height) * 0.5;
	clip.xy = round(clip.xy / clip.w * grid) / grid * clip.w;
	POSITION = clip;
	affine_uv = vec3(UV * clip.w, clip.w);
}

void fragment() {
	vec2 affine = affine_uv.xy / affine_uv.z;
	vec2 uv = mix(UV, affine, affine_amount);
	vec2 cell = floor(uv * checker_cells);
	vec3 color = mix(color_a.rgb, color_b.rgb, mod(cell.x + cell.y, 2.0)) * texture(albedo_texture, uv).rgb;
	ivec2 pixel = ivec2(mod(FRAGCOORD.xy, 4.0));
	int index = pixel.x + pixel.y * 4;
	int bayer[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	float threshold = (float(bayer[index]) + 0.5) / 16.0 - 0.5;
	color = floor(color * color_levels + 0.5 + threshold * dither_amount) / color_levels;
	ALBEDO = color;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}
