shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.25, 0.6, 0.85, 1.0);
uniform float hue_variation : hint_range(0.0, 1.0) = 0.35;
uniform float brightness_variation : hint_range(0.0, 1.0) = 0.3;
uniform float height_variation : hint_range(0.0, 2.0) = 0.8;
uniform float bob_height : hint_range(0.0, 1.0) = 0.12;
uniform float bob_speed : hint_range(0.0, 10.0) = 2.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.6;

varying vec3 instance_tint;

uint mix_bits(uint h) {
	h ^= h >> 16u;
	h *= 0x85ebca6bu;
	h ^= h >> 13u;
	h *= 0xc2b2ae35u;
	h ^= h >> 16u;
	return h;
}

float instance_random(int index, int salt) {
	return float(mix_bits(uint(index) * 2654435761u + uint(salt) * 97u)) / 4294967295.0;
}

vec3 hue_rotate(vec3 color, float angle) {
	vec3 axis = vec3(0.57735);
	float c = cos(angle);
	return color * c + cross(axis, color) * sin(angle) + axis * dot(axis, color) * (1.0 - c);
}

void vertex() {
	int id = INSTANCE_ID;
	float height_scale = 1.0 + (instance_random(id, 1) - 0.3) * height_variation;
	float base = -0.25;
	VERTEX.y = base + (VERTEX.y - base) * max(height_scale, 0.1);
	VERTEX.y += bob_height * (0.5 + 0.5 * sin(TIME * bob_speed + instance_random(id, 2) * TAU));
	vec3 tint = hue_rotate(base_color.rgb, (instance_random(id, 3) - 0.5) * hue_variation * TAU);
	instance_tint = tint * (1.0 + (instance_random(id, 4) - 0.5) * brightness_variation);
}

void fragment() {
	ALBEDO = instance_tint;
	ROUGHNESS = roughness;
}
