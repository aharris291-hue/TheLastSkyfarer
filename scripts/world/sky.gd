extends CanvasLayer
class_name SkyLayer
## Full-screen painted sky behind the world. Reads the camera so clouds
## drift with parallax, and blends palettes when the time of day changes.

const PALETTES := {
	"dawn": {"sky_top": Color(0.42, 0.52, 0.78), "sky_mid": Color(0.86, 0.72, 0.78),
		"horizon_col": Color(1.0, 0.8, 0.62), "sun_col": Color(1.0, 0.78, 0.5),
		"cloud_light": Color(1.0, 0.9, 0.85), "cloud_shade": Color(0.72, 0.64, 0.78),
		"sun_pos": Vector2(0.78, 0.5), "stars": 0.0, "tint": Color(1.0, 0.93, 0.88)},
	"day": {"sky_top": Color(0.3, 0.55, 0.88), "sky_mid": Color(0.6, 0.8, 0.97),
		"horizon_col": Color(0.92, 0.95, 0.98), "sun_col": Color(1.0, 0.95, 0.8),
		"cloud_light": Color(1.0, 1.0, 1.0), "cloud_shade": Color(0.75, 0.8, 0.9),
		"sun_pos": Vector2(0.62, 0.12), "stars": 0.0, "tint": Color(1, 1, 1)},
	"sunset": {"sky_top": Color(0.32, 0.3, 0.6), "sky_mid": Color(0.92, 0.55, 0.45),
		"horizon_col": Color(1.0, 0.72, 0.42), "sun_col": Color(1.0, 0.6, 0.3),
		"cloud_light": Color(1.0, 0.8, 0.65), "cloud_shade": Color(0.62, 0.45, 0.6),
		"sun_pos": Vector2(0.22, 0.52), "stars": 0.0, "tint": Color(1.0, 0.84, 0.74)},
	"night": {"sky_top": Color(0.04, 0.06, 0.16), "sky_mid": Color(0.1, 0.14, 0.3),
		"horizon_col": Color(0.25, 0.3, 0.48), "sun_col": Color(0.75, 0.82, 1.0),
		"cloud_light": Color(0.55, 0.6, 0.78), "cloud_shade": Color(0.2, 0.24, 0.4),
		"sun_pos": Vector2(0.3, 0.18), "stars": 1.0, "tint": Color(0.55, 0.62, 0.85)},
}

var rect: ColorRect
var mat: ShaderMaterial
var modulate_node: CanvasModulate
var camera: Camera2D
var base_horizon := 0.62
var ground_y := 900.0


func _init() -> void:
	layer = -10
	follow_viewport_enabled = false


func _ready() -> void:
	rect = ColorRect.new()
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mat = ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/sky.gdshader")
	rect.material = mat
	add_child(rect)


func setup(cam: Camera2D, canvas_mod: CanvasModulate, tod: String) -> void:
	camera = cam
	modulate_node = canvas_mod
	apply(tod, 0.0)


func apply(tod: String, duration := 2.5) -> void:
	var pal: Dictionary = PALETTES.get(tod, PALETTES["day"])
	for k in pal.keys():
		if k == "tint":
			if modulate_node:
				if duration > 0.0:
					create_tween().tween_property(modulate_node, "color", pal[k], duration)
				else:
					modulate_node.color = pal[k]
			continue
		if duration > 0.0:
			var from = mat.get_shader_parameter(k)
			if from == null:
				from = pal[k]
			create_tween().tween_method(func(v): mat.set_shader_parameter(k, v), from, pal[k], duration)
		else:
			mat.set_shader_parameter(k, pal[k])


func set_fog(amount: float) -> void:
	mat.set_shader_parameter("fog", amount)


func _process(_delta: float) -> void:
	if camera == null:
		return
	var c := camera.get_screen_center_position()
	mat.set_shader_parameter("cam", c)
	# Horizon sits a little below the ground line and shifts gently with camera height.
	var h := clampf(base_horizon + (ground_y - c.y) * 0.00012, 0.45, 0.8)
	mat.set_shader_parameter("horizon", h)
