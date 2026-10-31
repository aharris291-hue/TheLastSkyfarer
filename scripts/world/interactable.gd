extends Area2D
class_name Interactable
## Anything Kieran can inspect or talk to. Picks a dialogue from `rules`:
## an array of {"if": condition, "dialogue": id, "do": actions}; the first
## rule whose condition passes is used.

signal interacted(by: Node)

@export var prompt := "Inspect"
@export var size := Vector2(140, 200)
@export var show_marker := true
var rules: Array = []
var available_if = null          # condition string/array; null = always
var marker: Node2D


func _ready() -> void:
	add_to_group("interactable")
	collision_layer = 4
	collision_mask = 0
	monitoring = false
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = size
	shape.shape = rect
	shape.position = Vector2(0, -size.y * 0.5)
	add_child(shape)
	if show_marker:
		marker = preload("res://scripts/world/interact_marker.gd").new()
		marker.position = Vector2(0, -size.y - 30)
		add_child(marker)
	GameState.flag_changed.connect(func(_f, _v): _refresh())
	GameState.quest_changed.connect(func(_q): _refresh())
	GameState.objective_changed.connect(func(_q): _refresh())
	_refresh.call_deferred()


func _refresh() -> void:
	if marker:
		marker.visible = can_interact() and _has_new_content()


func _has_new_content() -> bool:
	## Marker shows only while the rule that would fire is not a repeat line.
	var r := _pick_rule()
	return not r.is_empty() and not r.get("repeat", false)


func can_interact() -> bool:
	return GameState.check(available_if) and not _pick_rule().is_empty()


func prompt_text() -> String:
	return prompt


func _pick_rule() -> Dictionary:
	for r in rules:
		if GameState.check(r.get("if")):
			return r
	return {}


func interact(by: Node) -> void:
	var r := _pick_rule()
	if r.is_empty():
		return
	AudioManager.play_sfx("interact", 0.05, -4.0)
	interacted.emit(by)
	_on_interact(by)
	if r.has("dialogue"):
		await DialogueUI.play(r["dialogue"])
	if r.has("do"):
		GameState.run_actions(r["do"])
	_refresh()


func _on_interact(_by: Node) -> void:
	pass
