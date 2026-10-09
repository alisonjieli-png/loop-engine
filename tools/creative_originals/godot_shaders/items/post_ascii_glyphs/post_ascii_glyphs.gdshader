shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float cell_pixels : hint_range(4.0, 32.0) = 8.0;
uniform bool use_scene_color = true;
uniform vec4 text_color : source_color = vec4(0.4, 1.0, 0.5, 1.0);
uniform vec4 background_color : source_color = vec4(0.02, 0.03, 0.04, 1.0);
uniform float contrast : hint_range(0.5, 3.0) = 1.3;
uniform float color_boost : hint_range(0.5, 3.0) = 1.4;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

const int GLYPHS[10] = int[10](0, 4194304, 131200, 14336, 459200, 4357252, 27070835, 11512810, 31913518, 33554431);

void fragment() {
	vec2 pixel = SCREEN_UV * VIEWPORT_SIZE;
	vec2 cell = floor(pixel / cell_pixels);
	vec2 cell_uv = (cell + 0.5) * cell_pixels / VIEWPORT_SIZE;
	float level = log2(cell_pixels);
	vec3 color = textureLod(screen_texture, cell_uv, level).rgb;
	float l = clamp((luminance(color) - 0.5) * contrast + 0.5, 0.0, 1.0);
	int index = int(min(l * 10.0, 9.0));
	vec2 local = fract(pixel / cell_pixels);
	vec2 inner = (local - 0.1) / 0.8;
	float ink = 0.0;
	if (inner.x >= 0.0 && inner.x < 1.0 && inner.y >= 0.0 && inner.y < 1.0) {
		int column = int(inner.x * 5.0);
		int row = int(inner.y * 5.0);
		ink = float((GLYPHS[index] >> (row * 5 + column)) & 1);
	}
	vec3 glyph_color = use_scene_color ? color * color_boost : text_color.rgb;
	ALBEDO = mix(background_color.rgb, glyph_color, ink);
}
