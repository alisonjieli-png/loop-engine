shader_type spatial;
render_mode cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 smoke_color : source_color = vec4(0.62, 0.62, 0.65, 1.0);
uniform float density : hint_range(0.0, 2.0) = 1.0;
uniform float noise_scale : hint_range(0.5, 12.0) = 3.5;
uniform float churn_speed : hint_range(0.0, 3.0) = 0.35;
uniform float softness : hint_range(0.05, 1.0) = 0.45;
uniform float roundness : hint_range(0.0, 1.0) = 0.7;
uniform float detail_normal : hint_range(0.0, 2.0) = 0.6;

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

float hash31(vec3 p) {
	ivec3 c = ivec3(floor(p));
	return float(fmix32(uint(c.x) * 73856093u ^ uint(c.y) * 19349663u ^ uint(c.z) * 83492791u)) / 4294967295.0;
}

float value_noise3(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	float n000 = hash31(cell);
	float n100 = hash31(cell + vec3(1.0, 0.0, 0.0));
	float n010 = hash31(cell + vec3(0.0, 1.0, 0.0));
	float n110 = hash31(cell + vec3(1.0, 1.0, 0.0));
	float n001 = hash31(cell + vec3(0.0, 0.0, 1.0));
	float n101 = hash31(cell + vec3(1.0, 0.0, 1.0));
	float n011 = hash31(cell + vec3(0.0, 1.0, 1.0));
	float n111 = hash31(cell + vec3(1.0, 1.0, 1.0));
	float x00 = mix(n000, n100, u.x);
	float x10 = mix(n010, n110, u.x);
	float x01 = mix(n001, n101, u.x);
	float x11 = mix(n011, n111, u.x);
	return mix(mix(x00, x10, u.y), mix(x01, x11, u.y), u.z);
}

float fbm3(vec3 p, int octaves) {
	float total = 0.0;
	float amplitude = 0.5;
	float norm = 0.0;
	for (int i = 0; i < octaves; i++) {
		total += amplitude * value_noise3(p);
		norm += amplitude;
		p = p * 2.07 + vec3(11.3, 5.7, 3.1);
		amplitude *= 0.5;
	}
	return total / norm;
}

void vertex() {
	// Spherical billboard: keep the node's position and scale, take the rotation from the camera.
	vec3 scale = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
	mat4 facing = mat4(INV_VIEW_MATRIX[0] * scale.x, INV_VIEW_MATRIX[1] * scale.y, INV_VIEW_MATRIX[2] * scale.z,
					   MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = VIEW_MATRIX * facing;
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 p = (UV - 0.5) * 2.0;
	float t = TIME * churn_speed;
	float n = fbm3(vec3(p * noise_scale * 0.5, t), 4);
	float radius = length(p) + (n - 0.5) * 0.6;
	float alpha = (1.0 - smoothstep(1.0 - softness, 1.0, radius)) * density * (0.55 + n * 0.6);
	if (alpha < 0.01) {
		discard;
	}
	float e = 0.05;
	float nx = fbm3(vec3((p + vec2(e, 0.0)) * noise_scale * 0.5, t), 4) - n;
	float ny = fbm3(vec3((p + vec2(0.0, e)) * noise_scale * 0.5, t), 4) - n;
	float z = sqrt(max(1.0 - dot(p, p), 0.0));
	vec3 sphere = normalize(vec3(p.x, -p.y, mix(1.0, z, roundness)));
	NORMAL = normalize(sphere - vec3(nx, -ny, 0.0) * detail_normal * 10.0);
	ALBEDO = smoke_color.rgb;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
	ALPHA = clamp(alpha, 0.0, 1.0);
}
