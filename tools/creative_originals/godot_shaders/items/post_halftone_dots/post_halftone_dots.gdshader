shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, skip_vertex_transform, fog_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float dot_spacing : hint_range(2.0, 40.0) = 7.0;
uniform float dot_softness : hint_range(0.0, 2.0) = 0.8;
uniform vec4 paper_color : source_color = vec4(0.97, 0.95, 0.9, 1.0);
uniform float ink_strength : hint_range(0.0, 1.5) = 1.0;
uniform bool monochrome = false;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

float screen_dot(vec2 pixel, float angle_degrees, float ink) {
	float angle = radians(angle_degrees);
	mat2 rotate = mat2(vec2(cos(angle), sin(angle)), vec2(-sin(angle), cos(angle)));
	vec2 p = rotate * pixel / dot_spacing;
	vec2 cell_center = floor(p) + 0.5;
	vec2 sample_pixel = transpose(rotate) * cell_center * dot_spacing;
	float radius = sqrt(clamp(ink, 0.0, 1.0)) * 0.7071;
	float distance_to_center = length(p - cell_center);
	float width = fwidth(distance_to_center) * dot_softness + 1e-4;
	return 1.0 - smoothstep(radius - width, radius + width, distance_to_center);
}

vec4 to_cmyk(vec3 rgb) {
	float k = 1.0 - max(max(rgb.r, rgb.g), rgb.b);
	vec3 cmy = (1.0 - rgb - k) / max(1.0 - k, 1e-4);
	return vec4(cmy, k);
}

void fragment() {
	vec3 color = textureLod(screen_texture, SCREEN_UV, 1.0).rgb;
	vec4 ink = to_cmyk(color) * ink_strength;
	vec2 pixel = FRAGCOORD.xy;
	if (monochrome) {
		float dark = 1.0 - dot(color, vec3(0.299, 0.587, 0.114));
		float dot_mask = screen_dot(pixel, 45.0, dark * ink_strength);
		ALBEDO = paper_color.rgb * (1.0 - dot_mask);
	} else {
		float c = screen_dot(pixel, 15.0, ink.x);
		float m = screen_dot(pixel, 75.0, ink.y);
		float y = screen_dot(pixel, 0.0, ink.z);
		float k = screen_dot(pixel, 45.0, ink.w);
		vec3 printed = paper_color.rgb * (vec3(1.0) - vec3(c, 0.0, 0.0)) * (vec3(1.0) - vec3(0.0, m, 0.0))
			* (vec3(1.0) - vec3(0.0, 0.0, y));
		ALBEDO = printed * (1.0 - k);
	}
}
