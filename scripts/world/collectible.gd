extends Interactable
class_name Collectible
## A journal page or other discovery. Collected by interacting with it.

@export var journal_id := ""
var _t := 0.0
var glow: Sprite2D


func _ready() -> void:
	prompt = "Pick up"
	size = Vector2(110, 120)
	show_marker = false
	rules = [{"if": "!collected_%s" % journal_id, "do": [{"set": "collected_%s" % journal_id}, {"journal": journal_id}]}]
	super._ready()
	glow = Sprite2D.new()
	glow.texture = preload("res://scripts/world/fx.gd").glow_texture()
	glow.modulate = Color(1.0, 0.9, 0.6, 0.8)
	glow.scale = Vector2(1.4, 1.4)
	glow.position = Vector2(0, -50)
	add_child(glow)
	var page := Sprite2D.new()
	page.texture = preload("res://scripts/world/fx.gd").page_texture()
	page.position = Vector2(0, -50)
	add_child(page)
	_update_visible()
	GameState.flag_changed.connect(func(_f, _v): _update_visible())


func _update_visible() -> void:
	visible = not GameState.has_flag("collected_%s" % journal_id)


func _process(delta: float) -> void:
	_t += delta
	if glow:
		glow.scale = Vector2.ONE * (1.3 + sin(_t * 2.5) * 0.15)
	for c in get_children():
		if c is Sprite2D:
			c.position.y = -50 + sin(_t * 2.0) * 6.0


func interact(by: Node) -> void:
	AudioManager.play_sfx("discovery")
	await super.interact(by)
