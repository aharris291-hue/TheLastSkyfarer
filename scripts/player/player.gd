extends CharacterBody2D
class_name Player
## Kieran Thorn — side-scrolling movement, gliding and interaction.
##
## Movement constants live here; the agreed values and their rationale are
## recorded in docs/GAME_DESIGN_GUIDELINES.md (Player movement).

signal landed
signal glide_started
signal glide_ended

const SPRITE_SCALE := 0.84         # frames are drawn at 2x the sheet size
const FEET_PAD := 6.0              # transparent rows under the feet in every frame
const ANIMS := {
	# name: [texture, frame count, fps, loop]
	"idle": ["res://assets/characters/kieran/kieran_idle.png", 5, 5.0, true],
	"walk": ["res://assets/characters/kieran/kieran_walk.png", 6, 10.0, true],
	"run": ["res://assets/characters/kieran/kieran_run.png", 6, 13.0, true],
	"jump": ["res://assets/characters/kieran/kieran_jump.png", 4, 10.0, false],
	"glide": ["res://assets/characters/kieran/kieran_glide.png", 3, 6.0, true],
}

@export var walk_speed := 330.0
@export var run_speed := 560.0
@export var ground_accel := 3400.0
@export var ground_friction := 4200.0
@export var air_accel := 2200.0
@export var jump_velocity := -1080.0
@export var jump_cut := 0.45           # velocity multiplier when jump is released early
@export var gravity_scale := 1.0
@export var max_fall := 1500.0
@export var coyote_time := 0.11
@export var jump_buffer := 0.13
@export var glide_fall := 150.0        # max fall speed while gliding
@export var glide_speed := 560.0
@export var glide_gravity := 0.18
@export var updraft_glide_gain := 1.0

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
var facing := -1
var locked := false                    # cutscenes / dialogue
var gliding := false
var can_glide := false
var updraft_force := 0.0               # set by Updraft areas while overlapping
var _coyote := 0.0
var _buffer := 0.0
var _was_on_floor := true
var _glide_toggle := false
var _interact_target: Node = null
var _step_frame := -1
var _idle_time := 0.0
var _auto_x := NAN
signal arrived

@onready var sprite: AnimatedSprite2D = $Sprite
@onready var interact_area: Area2D = $InteractArea


func _ready() -> void:
	add_to_group("player")
	_build_frames()
	sprite.scale = Vector2.ONE * SPRITE_SCALE
	sprite.play("idle")
	sprite.frame_changed.connect(_on_frame_changed)
	can_glide = GameState.has_flag("has_glider")
	GameState.flag_changed.connect(func(f, v):
		if f == "has_glider":
			can_glide = v)


func _build_frames() -> void:
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	for anim in ANIMS.keys():
		var def: Array = ANIMS[anim]
		var tex: Texture2D = load(def[0])
		var n: int = def[1]
		var fw := tex.get_width() / n
		frames.add_animation(anim)
		frames.set_animation_speed(anim, def[2])
		frames.set_animation_loop(anim, def[3])
		for i in n:
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2(i * fw, 0, fw, tex.get_height())
			frames.add_frame(anim, at)
	sprite.sprite_frames = frames
	# Feet sit at the node origin.
	sprite.centered = true
	var h := float(frames.get_frame_texture("idle", 0).get_height())
	sprite.offset = Vector2(0, -(h * 0.5 - FEET_PAD))


func _physics_process(delta: float) -> void:
	var input_dir := 0.0
	var controls := not locked and not DialogueUI.active
	if controls:
		input_dir = Input.get_axis("move_left", "move_right")
	if not is_nan(_auto_x):
		if absf(global_position.x - _auto_x) <= 8.0:
			_auto_x = NAN
			velocity.x = 0.0
			arrived.emit()
		else:
			input_dir = signf(_auto_x - global_position.x)
	var on_floor := is_on_floor()

	# Timers
	_coyote = coyote_time if on_floor else maxf(_coyote - delta, 0.0)
	_buffer = maxf(_buffer - delta, 0.0)
	if controls and Input.is_action_just_pressed("jump"):
		_buffer = jump_buffer

	# Horizontal movement
	var running := controls and Input.is_action_pressed("run")
	var target_speed := (run_speed if running else walk_speed) * input_dir
	if gliding:
		target_speed = glide_speed * input_dir if input_dir != 0.0 else velocity.x * 0.995
	var accel := ground_accel if on_floor else air_accel
	if absf(input_dir) < 0.01 and on_floor:
		velocity.x = move_toward(velocity.x, 0.0, ground_friction * delta)
	else:
		velocity.x = move_toward(velocity.x, target_speed, accel * delta)
	if input_dir != 0.0:
		facing = 1 if input_dir > 0 else -1

	# Jumping
	if _buffer > 0.0 and _coyote > 0.0:
		velocity.y = jump_velocity
		_buffer = 0.0
		_coyote = 0.0
		on_floor = false
		AudioManager.play_sfx("jump", 0.05)
		sprite.play("jump")
		sprite.frame = 0
	if controls and Input.is_action_just_released("jump") and velocity.y < 0.0 and not gliding:
		velocity.y *= jump_cut

	# Gliding
	var want_glide := false
	if can_glide and controls and not on_floor:
		if Settings.glide_hold:
			# Velocity only gates *starting* a glide, so updrafts can carry Kieran up.
			want_glide = Input.is_action_pressed("glide") and (gliding or velocity.y > -60.0)
		else:
			if Input.is_action_just_pressed("glide") and (gliding or velocity.y > -60.0):
				_glide_toggle = not _glide_toggle
			want_glide = _glide_toggle
	if on_floor:
		_glide_toggle = false
	if want_glide != gliding:
		gliding = want_glide
		if gliding:
			AudioManager.play_sfx("glide_open")
			glide_started.emit()
		else:
			glide_ended.emit()

	# Gravity
	if not on_floor:
		if gliding:
			velocity.y += gravity * glide_gravity * delta
			velocity.y -= updraft_force * updraft_glide_gain * delta
			velocity.y = clampf(velocity.y, -720.0, glide_fall)
		else:
			velocity.y += gravity * gravity_scale * delta
			velocity.y -= updraft_force * 0.35 * delta
			velocity.y = minf(velocity.y, max_fall)

	move_and_slide()

	on_floor = is_on_floor()
	if on_floor and not _was_on_floor:
		AudioManager.play_sfx("land", 0.05, -4.0)
		_squash()
		landed.emit()
	_was_on_floor = on_floor

	_update_animation(input_dir, on_floor, running)
	_update_interaction(controls)


func _update_animation(input_dir: float, on_floor: bool, running: bool) -> void:
	sprite.flip_h = facing < 0
	var anim := "idle"
	if gliding:
		anim = "glide"
	elif not on_floor:
		anim = "jump"
		# Hold the rising frame on the way up, the tuck frame on the way down.
		if sprite.animation == "jump" and not sprite.is_playing():
			sprite.frame = 1 if velocity.y < 0 else 3
	elif absf(velocity.x) > 20.0:
		anim = "run" if running and absf(velocity.x) > walk_speed + 20.0 else "walk"
	if anim == "idle" and on_floor and not locked:
		_idle_time += get_physics_process_delta_time()
	else:
		_idle_time = 0.0
	if sprite.animation != anim:
		sprite.play(anim)


func idle_time() -> float:
	return _idle_time


func _on_frame_changed() -> void:
	if not is_on_floor():
		return
	if sprite.animation in ["walk", "run"] and sprite.frame in [1, 4]:
		AudioManager.play_sfx("step", 0.12, -6.0)


func _squash() -> void:
	var tw := create_tween()
	sprite.scale = Vector2(SPRITE_SCALE * 1.1, SPRITE_SCALE * 0.9)
	tw.tween_property(sprite, "scale", Vector2.ONE * SPRITE_SCALE, 0.16).set_trans(Tween.TRANS_BACK)


# --- Interaction --------------------------------------------------------------

func _update_interaction(controls: bool) -> void:
	var best: Node = null
	var best_d := INF
	for a in interact_area.get_overlapping_areas():
		if a.is_in_group("interactable") and a.has_method("can_interact") and a.can_interact():
			var d := global_position.distance_squared_to(a.global_position)
			if d < best_d:
				best_d = d
				best = a
	if best != _interact_target:
		_interact_target = best
		if best:
			HUD.show_prompt(best.prompt_text())
		else:
			HUD.hide_prompt()
	if not controls:
		HUD.hide_prompt()
		_interact_target = null
		return
	if best and Input.is_action_just_pressed("interact") and is_on_floor():
		HUD.hide_prompt()
		_interact_target = null
		velocity.x = 0.0
		best.interact(self)


func face_towards(x: float) -> void:
	facing = 1 if x > global_position.x else -1
	sprite.flip_h = facing < 0


## Walk to an x position (used by short scripted moments). Await `arrived`.
func walk_to(x: float) -> void:
	locked = true
	_auto_x = x
	await arrived
	locked = false
