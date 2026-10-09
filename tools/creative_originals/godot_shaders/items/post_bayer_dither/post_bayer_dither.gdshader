shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform int levels : hint_range(2, 16) = 4;
uniform float dot_scale : hint_range(1.0, 8.0) = 2.0;
uniform bool one_bit = false;
uniform vec4 dark_color : source_color = vec4(0.1, 0.08, 0.16, 1.0);
uniform vec4 light_color : source_color = vec4(0.92, 0.9, 0.8, 1.0);
uniform float contrast : hint_range(0.5, 2.0) = 1.1;

float luminance(vec3 color) {
	return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float bayer8(vec2 pixel) {
	ivec2 p = ivec2(mod(pixel, 8.0));
	int value = 0;
	int x = p.x;
	int y = p.y;
	for (int bit = 0; bit <= 2; bit++) {
		int xb = (x >> bit) & 1;
		int yb = (y >> bit) & 1;
		value = value * 4 + ((xb ^ yb) << 1) + yb;
	}
	return (float(value) + 0.5) / 64.0;
}

void fragment() {
	vec2 cell = floor(FRAGCOORD.xy / dot_scale);
	vec2 uv = (cell + 0.5) * dot_scale / VIEWPORT_SIZE;
	vec3 color = textureLod(screen_texture, uv, 0.0).rgb;
	color = clamp((color - 0.5) * contrast + 0.5, 0.0, 1.0);
	float threshold = bayer8(cell);
	if (one_bit) {
		float l = luminance(color);
		ALBEDO = mix(dark_color.rgb, light_color.rgb, step(threshold, l));
	} else {
		float steps = float(levels - 1);
		ALBEDO = floor(color * steps + threshold) / steps;
	}
}
