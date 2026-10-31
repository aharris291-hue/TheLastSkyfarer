extends Camera2D
## Smooth side-scrolling camera with gentle look-ahead in the facing
## direction. Vertical motion is damped so jumps don't bounce the view.

var target: Node2D
var look_ahead := 170.0
var vertical_offset := -170.0
var _ahead := 0.0
var _y := 0.0


func _ready() -> void:
	position_smoothing_enabled = false
	process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	make_current()


func set_bounds(r: Rect2) -> void:
	limit_left = int(r.position.x)
	limit_top = int(r.position.y)
	limit_right = int(r.end.x)
	limit_bottom = int(r.end.y)
	limit_smoothed = true


func snap() -> void:
	if target == null:
		return
	_ahead = look_ahead * _facing()
	_y = target.global_position.y + vertical_offset
	global_position = Vector2(target.global_position.x + _ahead, _y)
	reset_smoothing()


func _facing() -> float:
	return float(target.get("facing")) if target.get("facing") != null else 1.0


func _physics_process(delta: float) -> void:
	if target == null:
		return
	var gliding: bool = target.get("gliding") == true
	var want_ahead := look_ahead * _facing() * (1.6 if gliding else 1.0)
	_ahead = lerpf(_ahead, want_ahead, 1.0 - exp(-delta * 2.0))
	var on_floor: bool = target.is_on_floor() if target.has_method("is_on_floor") else true
	var ty := target.global_position.y + vertical_offset
	# Follow vertical quickly when falling far or landing; slowly mid-jump.
	var rate := 6.0 if on_floor or gliding else 2.0
	if ty - _y > 260.0:
		rate = 8.0
	_y = lerpf(_y, ty, 1.0 - exp(-delta * rate))
	var tx := target.global_position.x + _ahead
	global_position = global_position.lerp(Vector2(tx, _y), 1.0 - exp(-delta * 7.0))
