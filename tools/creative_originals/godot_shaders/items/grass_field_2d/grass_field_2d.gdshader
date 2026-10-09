shader_type canvas_item;

uniform vec4 front_color : source_color = vec4(0.42, 0.72, 0.25, 1.0);
uniform vec4 back_color : source_color = vec4(0.12, 0.32, 0.12, 1.0);
uniform vec4 tip_color : source_color = vec4(0.8, 0.85, 0.45, 1.0);
uniform float blades : hint_range(10.0, 200.0) = 60.0;
uniform float blade_height : hint_range(0.1, 1.0) = 0.55;
uniform float wind_strength : hint_range(0.0, 0.3) = 0.06;
uniform float wind_speed : hint_range(0.0, 5.0) = 1.4;
uniform int layers : hint_range(1, 5) = 3;

// MurmurHash3 32-bit finalizer used as an integer hash.
uint fmix32(uint h) {
	h ^= h >> 16u;
	h *= 0x85ebca6bu;
	h ^= h >> 13u;
	h *= 0xc2b2ae35u;
	h ^= h >> 16u;
	return h;
}

uint lattice2(vec2 p) {
	ivec2 c = ivec2(floor(p));
	return fmix32(uint(c.x) * 73856093u ^ uint(c.y) * 19349663u);
}

float hash21(vec2 p) {
	return float(lattice2(p)) / 4294967295.0;
}

vec2 hash22(vec2 p) {
	uint h = lattice2(p);
	return vec2(float(h & 0xffffu), float(h >> 16u)) / 65535.0;
}

float blade_layer(vec2 uv, float layer, out float tip) {
	float count = blades * (1.0 + layer * 0.35);
	float coverage = 0.0;
	tip = 0.0;
	for (int k = -1; k <= 1; k++) {
		float index = floor(uv.x * count) + float(k);
		float base_x = (index + hash21(vec2(index, layer))) / count;
		float height = blade_height * mix(0.5, 1.0, hash21(vec2(index, layer + 5.0))) * (1.0 - layer * 0.15);
		float up = (1.0 - uv.y) / height;
		if (up < 0.0 || up > 1.0) {
			continue;
		}
		float lean = (hash21(vec2(index, layer + 9.0)) - 0.5) * 0.05;
		float wind = sin(TIME * wind_speed + base_x * 8.0 + layer) * wind_strength;
		float x = base_x + (lean + wind) * up * up;
		float width = (1.0 - up) * 0.6 / count;
		float inside = 1.0 - smoothstep(width * 0.7, width, abs(uv.x - x));
		if (inside > coverage) {
			coverage = inside;
			tip = up;
		}
	}
	return coverage;
}

void fragment() {
	vec3 color = vec3(0.0);
	float alpha = 0.0;
	for (int i = layers - 1; i >= 0; i--) {
		float layer = float(i);
		float tip;
		vec2 uv = UV + vec2(layer * 0.137, -layer * 0.06);
		float coverage = blade_layer(uv, layer, tip);
		vec3 shade = mix(front_color.rgb, back_color.rgb, layer / max(float(layers - 1), 1.0));
		vec3 blade = mix(shade * 0.7, mix(shade, tip_color.rgb, 0.4), tip);
		color = mix(color, blade, coverage);
		alpha = max(alpha, coverage);
	}
	COLOR = vec4(color, alpha);
}
