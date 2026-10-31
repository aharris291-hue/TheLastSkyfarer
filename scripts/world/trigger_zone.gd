extends Area2D
class_name TriggerZone
## Fires once (or every time) the player enters, if its condition passes.

signal triggered

@export var size := Vector2(200, 400)
@export var once := true
var condition = null
var actions: Array = []
var dialogue := ""
var once_flag := ""          # persisted flag so it never re-fires after loading
var callback: Callable


func _ready() -> void:
	collision_layer = 0
	collision_mask = 2
	monitorable = false
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = size
	shape.shape = rect
	shape.position = Vector2(0, -size.y * 0.5)
	add_child(shape)
	body_entered.connect(_on_body)


func _on_body(body: Node) -> void:
	if not body.is_in_group("player"):
		return
	if once_flag != "" and GameState.has_flag(once_flag):
		return
	if not GameState.check(condition):
		return
	if once_flag != "":
		GameState.set_flag(once_flag)
	if once:
		set_deferred("monitoring", false)
	triggered.emit()
	if callback.is_valid():
		callback.call()
	if dialogue != "":
		await DialogueUI.play(dialogue)
	GameState.run_actions(actions)
