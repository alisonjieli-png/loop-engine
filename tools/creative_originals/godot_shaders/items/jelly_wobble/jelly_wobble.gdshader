shader_type spatial;
render_mode cull_back;

uniform vec4 jelly_color : source_color = vec4(0.35, 0.9, 0.45, 0.82);
uniform vec4 core_color : source_color = vec4(0.85, 1.0, 0.6, 1.0);
uniform float bounce_period : hint_range(0.3, 5.0) = 1.6;
uniform float squash_amount : hint_range(0.0, 0.5) = 0.18;
uniform float wobble_amount : hint_range(0.0, 0.5) = 0.12;
uniform float wobble_frequency : hint_range(1.0, 30.0) = 11.0;
uniform float damping : hint_range(0.0, 10.0) = 3.0;
uniform float object_height : hint_range(0.1, 5.0) = 1.0;
uniform float gloss : hint_range(0.0, 1.0) = 0.9;

void vertex() {
	float t = mod(TIME, bounce_period);
	float decay = exp(-t * damping);
	float squash = squash_amount * cos(t * wobble_frequency) * decay;
	float height = clamp(VERTEX.y / object_height + 0.5, 0.0, 1.0);
	float stretch_y = 1.0 - squash;
	float stretch_xz = 1.0 / sqrt(max(stretch_y, 0.1));
	VERTEX.xz *= mix(1.0, stretch_xz, height);
	VERTEX.y = (VERTEX.y + object_height * 0.5) * stretch_y - object_height * 0.5;
	float sway = wobble_amount * sin(t * wobble_frequency * 0.7) * decay * height * height;
	VERTEX.x += sway;
	VERTEX.z += sway * 0.5;
}

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALBEDO = jelly_color.rgb;
	ALPHA = mix(1.0, jelly_color.a, facing);
	ROUGHNESS = 1.0 - gloss;
	SPECULAR = 0.7;
	EMISSION = core_color.rgb * pow(facing, 3.0) * 0.35;
	BACKLIGHT = jelly_color.rgb * 0.5;
}
