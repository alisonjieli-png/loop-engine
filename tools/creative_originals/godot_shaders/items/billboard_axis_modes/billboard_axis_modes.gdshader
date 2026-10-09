shader_type spatial;
render_mode cull_disabled;

uniform sampler2D card_texture : source_color, hint_default_white, filter_linear_mipmap;
uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform int mode : hint_range(0, 1) = 1;
uniform float alpha_cutoff : hint_range(0.0, 1.0) = 0.5;
uniform bool shade_as_upright = true;

void vertex() {
	vec3 scale = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
	vec3 origin = MODEL_MATRIX[3].xyz;
	mat3 basis;
	if (mode == 0) {
		basis = mat3(INV_VIEW_MATRIX[0].xyz, INV_VIEW_MATRIX[1].xyz, INV_VIEW_MATRIX[2].xyz);
	} else {
		vec3 to_camera = INV_VIEW_MATRIX[3].xyz - origin;
		vec3 forward = normalize(vec3(to_camera.x, 0.0, to_camera.z) + vec3(0.0, 0.0, 1e-5));
		vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
		basis = mat3(right, vec3(0.0, 1.0, 0.0), forward);
	}
	mat4 world = mat4(vec4(basis[0] * scale.x, 0.0), vec4(basis[1] * scale.y, 0.0), vec4(basis[2] * scale.z, 0.0),
					  vec4(origin, 1.0));
	MODELVIEW_MATRIX = VIEW_MATRIX * world;
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec4 texel = texture(card_texture, UV) * tint;
	if (texel.a < alpha_cutoff) {
		discard;
	}
	ALBEDO = texel.rgb;
	if (shade_as_upright) {
		NORMAL = normalize((VIEW_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz * 0.6 + NORMAL * 0.4);
	}
}
