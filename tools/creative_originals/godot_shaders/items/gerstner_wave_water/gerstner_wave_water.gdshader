shader_type spatial;

uniform vec4 deep_color : source_color = vec4(0.02, 0.1, 0.18, 1.0);
uniform vec4 shallow_color : source_color = vec4(0.06, 0.38, 0.45, 1.0);
uniform vec4 crest_color : source_color = vec4(0.8, 0.92, 0.95, 1.0);
uniform float amplitude : hint_range(0.0, 2.0) = 0.22;
uniform float wavelength : hint_range(0.5, 20.0) = 3.5;
uniform float steepness : hint_range(0.0, 1.0) = 0.65;
uniform float speed : hint_range(0.0, 4.0) = 1.0;
uniform float direction_degrees : hint_range(0.0, 360.0) = 25.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.06;
uniform float crest_threshold : hint_range(0.0, 1.0) = 0.55;

varying float crest;

void add_wave(vec2 position, float angle, float length_scale, float amplitude_scale, float time, int count,
			  inout vec3 offset, inout vec3 tangent, inout vec3 binormal) {
	vec2 direction = vec2(cos(angle), sin(angle));
	float k = TAU / (wavelength * length_scale);
	float omega = sqrt(9.8 * k);
	float a = amplitude * amplitude_scale;
	float q = steepness / max(k * a * float(count), 1e-4);
	float f = k * dot(direction, position) - omega * time;
	float s = sin(f);
	float c = cos(f);
	offset += vec3(q * a * direction.x * c, a * s, q * a * direction.y * c);
	tangent += vec3(-q * a * direction.x * direction.x * k * s, a * direction.x * k * c,
					-q * a * direction.x * direction.y * k * s);
	binormal += vec3(-q * a * direction.x * direction.y * k * s, a * direction.y * k * c,
					 -q * a * direction.y * direction.y * k * s);
}

void vertex() {
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 offset = vec3(0.0);
	vec3 tangent = vec3(1.0, 0.0, 0.0);
	vec3 binormal = vec3(0.0, 0.0, 1.0);
	float base = radians(direction_degrees);
	float time = TIME * speed;
	add_wave(world.xz, base, 1.0, 1.0, time, 3, offset, tangent, binormal);
	add_wave(world.xz, base + 0.7, 0.57, 0.5, time, 3, offset, tangent, binormal);
	add_wave(world.xz, base - 1.1, 0.33, 0.25, time, 3, offset, tangent, binormal);
	mat3 to_object = inverse(mat3(MODEL_MATRIX));
	VERTEX += to_object * offset;
	vec3 world_normal = normalize(cross(binormal, tangent));
	NORMAL = normalize(transpose(mat3(MODEL_MATRIX)) * world_normal);
	crest = offset.y / max(amplitude * 1.75, 1e-4);
}

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec3 water = mix(shallow_color.rgb, deep_color.rgb, clamp(facing * 1.3, 0.0, 1.0));
	float foam = smoothstep(crest_threshold, 1.0, crest);
	ALBEDO = mix(water, crest_color.rgb, foam);
	ROUGHNESS = mix(roughness, 0.6, foam);
	SPECULAR = 0.6;
}
