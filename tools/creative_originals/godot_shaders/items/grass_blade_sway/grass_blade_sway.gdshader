shader_type spatial;
render_mode cull_disabled;

uniform vec4 root_color : source_color = vec4(0.12, 0.26, 0.08, 1.0);
uniform vec4 tip_color : source_color = vec4(0.58, 0.78, 0.3, 1.0);
uniform float wind_angle_degrees : hint_range(0.0, 360.0) = 30.0;
uniform float wind_strength : hint_range(0.0, 1.0) = 0.25;
uniform float gust_scale : hint_range(0.05, 2.0) = 0.35;
uniform float gust_speed : hint_range(0.0, 5.0) = 1.2;
uniform float flutter : hint_range(0.0, 0.3) = 0.05;
uniform float taper : hint_range(0.0, 1.0) = 0.9;
uniform float translucency : hint_range(0.0, 1.0) = 0.4;

varying float height;

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

float value_noise(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float a = hash21(cell);
	float b = hash21(cell + vec2(1.0, 0.0));
	float c = hash21(cell + vec2(0.0, 1.0));
	float d = hash21(cell + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p, int octaves) {
	float total = 0.0;
	float amplitude = 0.5;
	float norm = 0.0;
	mat2 turn = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
	for (int i = 0; i < octaves; i++) {
		total += amplitude * value_noise(p);
		norm += amplitude;
		p = turn * p * 2.03 + vec2(17.13, 9.71);
		amplitude *= 0.5;
	}
	return total / norm;
}

void vertex() {
	height = clamp(1.0 - UV.y, 0.0, 1.0);
	vec3 root_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float angle = radians(wind_angle_degrees);
	vec2 wind_direction = vec2(cos(angle), sin(angle));
	float gust = value_noise(root_world.xz * gust_scale - wind_direction * TIME * gust_speed);
	float phase = hash21(floor(root_world.xz * 37.0)) * TAU;
	float bend = height * height * (wind_strength * (0.3 + gust) + flutter * sin(TIME * 7.0 + phase));
	vec3 push_world = vec3(wind_direction.x, 0.0, wind_direction.y) * bend;
	vec3 push = inverse(mat3(MODEL_MATRIX)) * push_world;
	VERTEX += push;
	VERTEX.y -= bend * bend * 0.5 * height;
}

void fragment() {
	float half_width = 0.5 * (1.0 - taper * height);
	if (abs(UV.x - 0.5) > half_width) {
		discard;
	}
	ALBEDO = mix(root_color.rgb, tip_color.rgb, height);
	ROUGHNESS = 0.8;
	BACKLIGHT = tip_color.rgb * translucency * height;
}
