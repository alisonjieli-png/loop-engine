shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.75, 0.7, 0.55, 1.0);
uniform vec4 caustic_color : source_color = vec4(0.65, 1.0, 0.95, 1.0);
uniform float caustic_scale : hint_range(0.2, 10.0) = 1.6;
uniform float caustic_strength : hint_range(0.0, 4.0) = 1.4;
uniform float sharpness : hint_range(1.0, 12.0) = 5.0;
uniform float drift_speed : hint_range(0.0, 2.0) = 0.25;
uniform float water_surface_height : hint_range(-20.0, 20.0) = 2.0;
uniform float depth_falloff : hint_range(0.0, 2.0) = 0.25;
uniform float roughness : hint_range(0.0, 1.0) = 0.9;

varying vec3 world_position;
varying vec3 world_normal;

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

// x: distance to the nearest feature point, y: to the second nearest, z: random value of the nearest cell.
vec3 voronoi(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	float f1 = 8.0;
	float f2 = 8.0;
	float id = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 neighbor = vec2(float(x), float(y));
			vec2 feature = hash22(cell + neighbor);
			float d = length(neighbor + feature - f);
			if (d < f1) {
				f2 = f1;
				f1 = d;
				id = hash21(cell + neighbor + vec2(0.37, 0.71) * 101.0);
			} else if (d < f2) {
				f2 = d;
			}
		}
	}
	return vec3(f1, f2, id);
}

float caustic_layer(vec2 p) {
	vec3 cells = voronoi(p);
	return pow(1.0 - clamp(cells.y - cells.x, 0.0, 1.0), sharpness);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec2 p = world_position.xz * caustic_scale;
	float t = TIME * drift_speed;
	float a = caustic_layer(p + vec2(t, t * 0.6));
	float b = caustic_layer(p * 1.3 + vec2(-t * 0.8, t * 0.9) + 5.0);
	float web = min(a, b) * 2.0 + a * b;
	float facing_up = clamp(world_normal.y, 0.0, 1.0);
	float depth = max(water_surface_height - world_position.y, 0.0);
	float strength = caustic_strength * facing_up * exp(-depth * depth_falloff);
	ALBEDO = albedo.rgb;
	ROUGHNESS = roughness;
	EMISSION = albedo.rgb * caustic_color.rgb * web * strength;
}
