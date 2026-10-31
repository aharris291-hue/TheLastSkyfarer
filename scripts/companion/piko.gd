extends Node2D
class_name Piko
## Piko — Kieran's companion spirit.
##
## Floats near Kieran's shoulder with spring-damped motion, reacts to the
## world, and senses hidden wind currents and Skyfarer traces (nodes in the
## "piko_sense" group that implement reveal()/is_revealed()). Piko does not
## speak yet: per the story documents his first words come hours later, so he
## communicates with chirps, trills and body language.

signal sensed(target: Node)

const SCALE := 0.3
const SENSE_RADIUS := 900.0

@export var follow_offset := Vector2(-95, -205)
var player: Node2D
var active := true
var _vel := Vector2.ZERO
var _t := 0.0
var _mode := "follow"          # follow, sense, perch, loop
var _sense_target: Node2D
var _sense_time := 0.0
var _cooldown := 2.0
var _loop_t := 0.0
var _facing := 1
var _glow_strength := 0.0

var body: Sprite2D
var glow: Sprite2D
var emote: Label


func _ready() -> void:
	add_to_group("piko")
	glow = Sprite2D.new()
	glow.texture = preload("res://scripts/world/fx.gd").glow_texture()
	glow.modulate = Color(0.6, 0.85, 1.0, 0.0)
	glow.scale = Vector2(2.6, 2.6)
	add_child(glow)
	body = Sprite2D.new()
	body.texture = load("res://assets/characters/piko/piko_side.png")
	body.scale = Vector2.ONE * SCALE
	body.offset = Vector2(-40, 0)   # pivot near the body rather than the tail
	add_child(body)
	emote = Label.new()
	emote.add_theme_font_size_override("font_size", 46)
	emote.add_theme_color_override("font_outline_color", Color(0.1, 0.1, 0.2))
	emote.add_theme_constant_override("outline_size", 8)
	emote.position = Vector2(-14, -130)
	emote.visible = false
	add_child(emote)


func attach(p: Node2D) -> void:
	player = p
	global_position = p.global_position + follow_offset


func _process(delta: float) -> void:
	_t += delta
	if player == null or not active:
		return
	var target := _follow_target()
	match _mode:
		"sense":
			if not is_instance_valid(_sense_target):
				_mode = "follow"
			else:
				target = _sense_target.global_position + Vector2(0, -120 + sin(_t * 4.0) * 12.0)
				_sense_time += delta
				var near_player := player.global_position.distance_to(_sense_target.global_position) < 750.0
				if _sense_time > 1.2 and near_player and _sense_target.has_method("reveal"):
					_sense_target.reveal()
					_show_emote("✦")
					sensed.emit(_sense_target)
					_mode = "follow"
					_cooldown = 3.0
				elif _sense_time > 7.0:
					_mode = "follow"
					_cooldown = 4.0
		"loop":
			_loop_t += delta
			target += Vector2(cos(_loop_t * 6.0) * 70.0, sin(_loop_t * 6.0) * 70.0)
			if _loop_t > PI * 2 / 6.0 * 1.0 + 0.05:
				_mode = "follow"
		"perch":
			target = player.global_position + Vector2(-20 * _player_facing(), -175)

	# Spring-damper toward the target: lively but never jittery.
	var k := 22.0
	var damping := 7.5
	var accel := (target - global_position) * k - _vel * damping
	_vel += accel * delta
	global_position += _vel * delta
	if global_position.distance_to(target) > 1600.0:
		global_position = target    # teleport if separated (e.g. respawn)
		_vel = Vector2.ZERO

	# Face the direction of travel; the source art faces left.
	if absf(_vel.x) > 40.0:
		_facing = 1 if _vel.x > 0 else -1
	body.flip_h = _facing > 0
	body.offset.x = 40 if _facing > 0 else -40
	# Tail sway and a little tilt with speed.
	body.skew = sin(_t * 3.2) * 0.04
	body.rotation = clampf(_vel.x / 4000.0, -0.25, 0.25)

	# Markings glow near Skyfarer traces (a hint, not a solution).
	var want_glow := 0.0
	if _mode == "sense":
		want_glow = 0.8
	elif _nearest_sense() != null:
		want_glow = 0.35
	_glow_strength = lerpf(_glow_strength, want_glow, delta * 3.0)
	glow.modulate.a = _glow_strength * (0.75 + sin(_t * 5.0) * 0.25)
	body.modulate = Color(1, 1, 1).lerp(Color(0.85, 0.95, 1.25), _glow_strength)

	_cooldown -= delta
	if _cooldown <= 0.0 and _mode == "follow":
		_think()


func _player_facing() -> int:
	return player.facing if "facing" in player else 1


func _follow_target() -> Vector2:
	var f := _player_facing()
	var off := Vector2(follow_offset.x * f, follow_offset.y)
	if player.get("gliding"):
		off = Vector2(-150 * f, -150)
	return player.global_position + off + Vector2(0, sin(_t * 2.2) * 14.0)


func _nearest_sense() -> Node2D:
	var best: Node2D = null
	var best_d := SENSE_RADIUS
	for n in get_tree().get_nodes_in_group("piko_sense"):
		if n.has_method("is_revealed") and n.is_revealed():
			continue
		var d := global_position.distance_to(n.global_position)
		if d < best_d:
			best_d = d
			best = n
	return best


func _think() -> void:
	var s := _nearest_sense()
	if s != null:
		_mode = "sense"
		_sense_target = s
		_sense_time = 0.0
		_show_emote("!")
		AudioManager.play_sfx("piko_trill")
		GameState.notify.emit("Piko senses something nearby", "discovery")
		return
	# Idle personality: a happy loop when Kieran stands still for a while.
	if player.has_method("idle_time") and player.idle_time() > 6.0 and randf() < 0.5:
		_mode = "loop"
		_loop_t = 0.0
		AudioManager.play_sfx("piko_chirp", 0.1)
		_cooldown = 9.0
		return
	_cooldown = 1.0


func react(symbol := "?", sound := "piko_chirp") -> void:
	_show_emote(symbol)
	AudioManager.play_sfx(sound, 0.08)


func _show_emote(symbol: String) -> void:
	emote.text = symbol
	emote.visible = true
	emote.modulate.a = 1.0
	var tw := create_tween()
	tw.tween_interval(1.0)
	tw.tween_property(emote, "modulate:a", 0.0, 0.5)
	tw.tween_callback(func(): emote.visible = false)
