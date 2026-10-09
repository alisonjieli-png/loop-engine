shader_type spatial;

uniform vec4 rock_light : source_color = vec4(0.58, 0.55, 0.5, 1.0);
uniform vec4 rock_dark : source_color = vec4(0.3, 0.28, 0.26, 1.0);
uniform vec4 crevice_color : source_color = vec4(0.12, 0.11, 0.1, 1.0);
uniform float scale : hint_range(0.1, 10.0) = 1.6;
uniform float blend_sharpness : hint_range(1.0, 16.0) = 6.0;
uniform float crack_amount : hint_range(0.0, 1.0) = 0.5;
uniform float bump_strength : hint_range(0.0, 4.0) = 1.2;
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

// Bump mapping from a scalar height without tangents (screen-space surface gradient).
vec3 bump_normal(vec3 normal, vec3 position, float height, float strength) {
	vec3 dpdx = dFdx(position);
	vec3 dpdy = dFdy(position);
	float dhdx = dFdx(height);
	float dhdy = dFdy(height);
	vec3 r1 = cross(dpdy, normal);
	vec3 r2 = cross(normal, dpdx);
	float det = dot(dpdx, r1);
	vec3 gradient = sign(det) * (dhdx * r1 + dhdy * r2);
	return normalize(abs(det) * normal - strength * gradient);
}

vec2 rock_layer(vec2 p) {
	float body = fbm(p, 5);
	float ridge = 1.0 - abs(fbm(p * 2.3 + vec2(7.1, 3.3), 4) * 2.0 - 1.0);
	float crack = smoothstep(0.82, 0.97, ridge) * crack_amount;
	return vec2(body, crack);
}

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 weights = pow(abs(world_normal), vec3(blend_sharpness));
	weights /= max(weights.x + weights.y + weights.z, 1e-5);
	vec3 p = world_position * scale;
	vec2 layer = rock_layer(p.zy) * weights.x + rock_layer(p.xz + 13.7) * weights.y + rock_layer(p.xy + 29.1) * weights.z;
	vec3 color = mix(rock_dark.rgb, rock_light.rgb, smoothstep(0.3, 0.75, layer.x));
	color = mix(color, crevice_color.rgb, layer.y);
	ALBEDO = color;
	ROUGHNESS = roughness;
	float height = layer.x - layer.y * 0.6;
	NORMAL = bump_normal(NORMAL, VERTEX, height, bump_strength);
}
