shader_type canvas_item;

uniform vec4 sky_top : source_color = vec4(0.25, 0.5, 0.88, 1.0);
uniform vec4 sky_bottom : source_color = vec4(0.7, 0.85, 0.98, 1.0);
uniform vec4 cloud_light : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 cloud_shadow : source_color = vec4(0.55, 0.6, 0.72, 1.0);
uniform float coverage : hint_range(0.0, 1.0) = 0.5;
uniform float softness : hint_range(0.01, 0.5) = 0.15;
uniform float scale : hint_range(0.5, 20.0) = 3.0;
uniform float wind_speed : hint_range(-1.0, 1.0) = 0.03;
uniform float sun_angle_degrees : hint_range(0.0, 360.0) = 300.0;
uniform float shading : hint_range(0.0, 2.0) = 1.0;

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

float clouds(vec2 p) {
	return fbm(p, 6);
}

void fragment() {
	vec2 p = UV * vec2(scale * 1.6, scale) + vec2(TIME * wind_speed * scale, 0.0);
	float density = clouds(p);
	float mask = smoothstep(1.0 - coverage - softness, 1.0 - coverage + softness, density);
	float angle = radians(sun_angle_degrees);
	vec2 toward_sun = vec2(cos(angle), sin(angle)) * 0.12;
	float occlusion = clamp((clouds(p + toward_sun) - density) * 4.0 * shading, 0.0, 1.0);
	vec3 cloud = mix(cloud_light.rgb, cloud_shadow.rgb, occlusion);
	vec3 sky = mix(sky_top.rgb, sky_bottom.rgb, UV.y);
	COLOR = vec4(mix(sky, cloud, mask), 1.0);
}
