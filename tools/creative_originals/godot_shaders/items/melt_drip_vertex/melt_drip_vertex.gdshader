shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.95, 0.85, 0.62, 1.0);
uniform vec4 melted_color : source_color = vec4(0.98, 0.75, 0.45, 1.0);
uniform float melt : hint_range(0.0, 1.0) = 0.45;
uniform float object_height : hint_range(0.1, 10.0) = 1.2;
uniform float sag : hint_range(0.0, 1.0) = 0.35;
uniform float drip_length : hint_range(0.0, 1.0) = 0.25;
uniform float drip_thickness : hint_range(0.0, 0.2) = 0.05;
uniform int drip_count : hint_range(1, 24) = 9;
uniform float puddle_spread : hint_range(0.0, 1.0) = 0.4;
uniform bool loop_animation = false;

varying float melt_mask;

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

void vertex() {
	float amount = loop_animation ? 0.5 - 0.5 * cos(TIME * 0.5) : melt;
	float base = -object_height * 0.5;
	float h = clamp((VERTEX.y - base) / object_height, 0.0, 1.0);
	float angle = atan(VERTEX.z, VERTEX.x);
	float drip_slot = floor((angle / TAU + 0.5) * float(drip_count));
	float drip_center = (drip_slot + 0.5) / float(drip_count) * TAU - PI;
	float drip_shape = pow(max(cos((angle - drip_center) * float(drip_count) * 0.5), 0.0), 6.0);
	float reach = drip_length * amount * (0.4 + 0.6 * hash21(vec2(drip_slot, 3.0)));
	float drip_end = 1.0 - reach;
	float above_end = smoothstep(drip_end - 0.03, drip_end + 0.02, h);
	float bead = exp(-pow((h - drip_end) / 0.05, 2.0));
	float bulge = drip_shape * (above_end * 0.6 + bead) * drip_thickness * step(0.001, reach);
	vec2 outward = normalize(VERTEX.xz + vec2(1e-5));
	VERTEX.xz += outward * bulge * length(VERTEX.xz) / max(length(VERTEX.xz), 1e-3);
	VERTEX.y -= amount * sag * object_height * h * h;
	VERTEX.y = max(VERTEX.y, base);
	float near_base = 1.0 - smoothstep(0.0, 0.25, (VERTEX.y - base) / object_height);
	VERTEX.xz *= 1.0 + near_base * puddle_spread * amount * 1.5;
	melt_mask = clamp(amount * h + bulge * 12.0, 0.0, 1.0);
}

void fragment() {
	ALBEDO = mix(albedo.rgb, melted_color.rgb, melt_mask);
	ROUGHNESS = mix(0.6, 0.12, melt_mask);
	SPECULAR = 0.6;
}
