shader_type spatial;

uniform vec4 ice_color : source_color = vec4(0.62, 0.82, 0.95, 1.0);
uniform vec4 deep_color : source_color = vec4(0.12, 0.32, 0.58, 1.0);
uniform vec4 crack_color : source_color = vec4(0.95, 0.98, 1.0, 1.0);
uniform float cell_scale : hint_range(1.0, 30.0) = 5.0;
uniform float crack_width : hint_range(0.0, 0.2) = 0.035;
uniform float inner_depth : hint_range(0.0, 0.5) = 0.15;
uniform float inner_strength : hint_range(0.0, 1.0) = 0.55;
uniform float frost_rim : hint_range(0.0, 4.0) = 1.2;
uniform float roughness : hint_range(0.0, 1.0) = 0.12;

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

float crack_lines(vec2 p) {
	vec3 cells = voronoi(p);
	return 1.0 - smoothstep(0.0, crack_width, cells.y - cells.x);
}

void fragment() {
	vec3 view_tangent = normalize(vec3(dot(VIEW, TANGENT), dot(VIEW, -BINORMAL), dot(VIEW, NORMAL)));
	vec2 p = UV * cell_scale;
	float surface = crack_lines(p);
	vec2 parallax = view_tangent.xy / max(view_tangent.z, 0.25) * inner_depth * cell_scale;
	float inner = crack_lines(p * 1.37 + vec2(3.1, 7.7) - parallax) * inner_strength;
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec3 body = mix(ice_color.rgb, deep_color.rgb, facing * 0.65);
	body = mix(body, crack_color.rgb, max(surface, inner * (0.5 + 0.5 * facing)));
	ALBEDO = body;
	ROUGHNESS = mix(roughness, 0.55, surface);
	SPECULAR = 0.65;
	EMISSION = ice_color.rgb * pow(1.0 - facing, 3.0) * frost_rim * 0.35;
}
