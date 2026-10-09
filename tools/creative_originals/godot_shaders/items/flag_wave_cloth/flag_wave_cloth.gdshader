shader_type spatial;
render_mode cull_disabled;

uniform sampler2D flag_texture : source_color, hint_default_white;
uniform vec4 stripe_a : source_color = vec4(0.1, 0.25, 0.6, 1.0);
uniform vec4 stripe_b : source_color = vec4(0.95, 0.95, 0.92, 1.0);
uniform vec4 emblem_color : source_color = vec4(0.9, 0.7, 0.15, 1.0);
uniform int stripes : hint_range(0, 12) = 5;
uniform float amplitude : hint_range(0.0, 0.5) = 0.12;
uniform float wavelength : hint_range(0.1, 4.0) = 0.9;
uniform float speed : hint_range(0.0, 10.0) = 3.0;
uniform float droop : hint_range(0.0, 0.5) = 0.06;
uniform float flutter : hint_range(0.0, 1.0) = 0.35;

float wave_height(vec2 uv, float t) {
	float reach = uv.x;
	float k = TAU / wavelength;
	float main_wave = sin(k * uv.x - t * speed);
	float ripple = sin(k * 2.7 * uv.x - t * speed * 1.7 + uv.y * 4.0) * flutter;
	return amplitude * reach * (main_wave + ripple * 0.4);
}

void vertex() {
	vec2 uv = UV;
	float t = TIME;
	float e = 0.01;
	float h = wave_height(uv, t);
	float dhdu = (wave_height(uv + vec2(e, 0.0), t) - h) / e;
	float dhdv = (wave_height(uv + vec2(0.0, e), t) - h) / e;
	VERTEX.z += h;
	VERTEX.y -= droop * uv.x * uv.x;
	NORMAL = normalize(vec3(-dhdu, dhdv, 1.0));
}

void fragment() {
	vec3 color = stripe_b.rgb;
	if (stripes > 0) {
		float band = floor(UV.y * float(stripes));
		color = mod(band, 2.0) < 0.5 ? stripe_a.rgb : stripe_b.rgb;
	}
	vec2 emblem = (UV - vec2(0.3, 0.5)) * vec2(2.0, 1.2);
	color = mix(color, emblem_color.rgb, 1.0 - smoothstep(0.24, 0.26, length(emblem)));
	ALBEDO = color * texture(flag_texture, UV).rgb;
	ROUGHNESS = 0.85;
	BACKLIGHT = color * 0.3;
}
