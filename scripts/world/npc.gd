extends Interactable
class_name NPC
## A villager with a sprite who turns to face Kieran when spoken to.

@export var texture: Texture2D
@export var sprite_height := 330.0
@export var faces_right := false   # direction the source art faces
var sprite: Sprite2D
var _t := 0.0
var _base_scale := 1.0


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
	# Gentle breathing so villagers don't look like cardboard cut-outs.
	sprite.scale.y = _base_scale * (1.0 + sin(_t * 2.1) * 0.008)


func face(x: float) -> void:
	if sprite == null:
		return
	var want_right := x > global_position.x
	sprite.flip_h = want_right != faces_right


func _on_interact(by: Node) -> void:
	face(by.global_position.x)
	if by.has_method("face_towards"):
		by.face_towards(global_position.x)
