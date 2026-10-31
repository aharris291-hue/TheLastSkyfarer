extends Area2D
class_name Updraft
## A rising wind current. Lifts Kieran strongly while gliding.
## Hidden currents only appear once Piko senses them.

@export var size := Vector2(220, 700)
@export var force := 3400.0
@export var concealed := false
@export var reveal_flag := ""
var particles: CPUParticles2D
var _bodies: Array = []
var _sound: AudioStreamPlayer2D


func _ready() -> void:
	add_to_group("updraft")
	collision_layer = 8
	collision_mask = 2
	monitorable = false
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = size
	shape.shape = rect
	shape.position = Vector2(0, -size.y * 0.5)
	add_child(shape)
	particles = CPUParticles2D.new()
	particles.amount = int(size.x * size.y / 6000.0) + 12
	particles.lifetime = 2.2
	particles.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	particles.emission_rect_extents = Vector2(size.x * 0.45, 10)
	particles.direction = Vector2(0, -1)
	particles.spread = 6.0
	particles.gravity = Vector2.ZERO
	particles.initial_velocity_min = size.y / 2.4
	particles.initial_velocity_max = size.y / 1.8
	particles.scale_amount_min = 2.0
	particles.scale_amount_max = 5.0
	var grad := Gradient.new()
	grad.set_color(0, Color(0.85, 0.95, 1.0, 0.0))
	grad.set_color(1, Color(0.85, 0.95, 1.0, 0.0))
	grad.add_point(0.25, Color(0.9, 0.97, 1.0, 0.75))
	grad.add_point(0.8, Color(0.8, 0.93, 1.0, 0.5))
	particles.color_ramp = grad
	particles.position = Vector2(0, 0)
	add_child(particles)
	_sound = AudioStreamPlayer2D.new()
	_sound.stream = load("res://assets/audio/sfx/updraft_loop.wav")
	_sound.bus = "Ambience"
	_sound.max_distance = 1400.0
	_sound.position = Vector2(0, -size.y * 0.5)
	add_child(_sound)
	body_entered.connect(func(b): if b.is_in_group("player"): _bodies.append(b))
	body_exited.connect(func(b):
		_bodies.erase(b)
		if b.is_in_group("player"):
			b.updraft_force = 0.0)
	if reveal_flag != "" and GameState.has_flag(reveal_flag):
		concealed = false
	_apply_visibility()


func _apply_visibility() -> void:
	particles.emitting = not concealed
	monitoring = not concealed
	if not concealed and is_inside_tree():
		_sound.play()
	else:
		_sound.stop()


func reveal() -> void:
	if not concealed:
		return
	concealed = false
	if reveal_flag != "":
		GameState.set_flag(reveal_flag)
	_apply_visibility()
	AudioManager.play_sfx("gust")


## Where Piko should hover when sensing this current (its upper part,
## at the height Kieran actually flies past).
func sense_position() -> Vector2:
	return global_position + Vector2(0, -size.y * 0.6)


func is_revealed() -> bool:
	return not concealed


func _physics_process(_delta: float) -> void:
	for b in _bodies:
		if is_instance_valid(b):
			b.updraft_force = force
