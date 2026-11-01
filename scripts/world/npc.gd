extends Interactable
class_name NPC
## A villager with a sprite who turns to face Kieran when spoken to.

@export var texture: Texture2D
@export var sprite_height := 330.0
@export var faces_right := false   # direction the source art faces
var sprite: Sprite2D
var _t := 0.0
var _base_scale := 1.0
var _look_t := 0.0


func _ready() -> void:
	prompt = "Talk"
	size = Vector2(170, sprite_height)
	super._ready()
	if texture:
		sprite = Sprite2D.new()
		sprite.texture = texture
		_base_scale = sprite_height / texture.get_height()
		sprite.scale = Vector2.ONE * _base_scale
		sprite.centered = true
		sprite.offset = Vector2(0, -texture.get_height() * 0.5)
		add_child(sprite)
		move_child(sprite, 0)
	_t = randf() * 10.0


func _process(delta: float) -> void:
	if sprite == null:
		return
	_t += delta
	# Gentle breathing and a slight weight shift so villagers feel alive.
	sprite.scale.y = _base_scale * (1.0 + sin(_t * 2.1) * 0.012)
	sprite.skew = sin(_t * 0.9) * 0.012
	# Glance at Kieran when he comes close.
	_look_t -= delta
	if _look_t <= 0.0:
		_look_t = 0.4
		var p := get_tree().get_first_node_in_group("player") as Node2D
		if p and absf(p.global_position.x - global_position.x) < 320.0 \
				and absf(p.global_position.y - global_position.y) < 200.0:
			face(p.global_position.x)


func face(x: float) -> void:
	if sprite == null:
		return
	var want_right := x > global_position.x
	sprite.flip_h = want_right != faces_right


func _on_interact(by: Node) -> void:
	face(by.global_position.x)
	if by.has_method("face_towards"):
		by.face_towards(global_position.x)
