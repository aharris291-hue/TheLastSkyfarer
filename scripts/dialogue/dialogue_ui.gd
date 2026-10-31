extends CanvasLayer
## On-screen dialogue box with portraits, typewriter text and choices
## (autoload "DialogueUI"). Call `await DialogueUI.play("dialogue_id")`.

signal finished(id: String)
signal line_shown(speaker: String, text: String)

const BASE_FONT := 34
const CHARS_PER_SEC := 48.0

@onready var root: Control = $Root
@onready var panel: PanelContainer = $Root/Panel
@onready var portrait_rect: TextureRect = $Root/Panel/HBox/Portrait
@onready var name_label: Label = $Root/Panel/HBox/VBox/Name
@onready var text_label: RichTextLabel = $Root/Panel/HBox/VBox/Text
@onready var choices_box: VBoxContainer = $Root/Panel/HBox/VBox/Choices
@onready var hint_label: Label = $Root/Panel/HBox/VBox/Hint

var active := false
var _typing := false
var _advance_requested := false
var _choice_made := ""
var _current_id := ""


func _ready() -> void:
	layer = 50
	process_mode = Node.PROCESS_MODE_ALWAYS
	root.visible = false
	Settings.changed.connect(_apply_text_scale)
	_apply_text_scale()


func _apply_text_scale() -> void:
	var s := int(BASE_FONT * Settings.text_scale)
	text_label.add_theme_font_size_override("normal_font_size", s)
	text_label.add_theme_font_size_override("italics_font_size", s)
	text_label.add_theme_font_size_override("bold_font_size", s)
	name_label.add_theme_font_size_override("font_size", int(s * 1.05))
	hint_label.text = "%s  continue" % Settings.action_label("advance")


func _unhandled_input(event: InputEvent) -> void:
	if not active or choices_box.visible:
		return
	if event.is_action_pressed("advance") or event.is_action_pressed("ui_accept"):
		_advance_requested = true
		get_viewport().set_input_as_handled()


func play(id: String) -> void:
	if active:
		await finished
	if not DialogueDB.has(id):
		push_error("Unknown dialogue %s" % id)
		return
	active = true
	_current_id = id
	root.visible = true
	await get_tree().process_frame
	var steps: Array = DialogueDB.get_dialogue(id)
	var i := 0
	var guard := 0
	while i < steps.size() and guard < 500:
		guard += 1
		var step: Dictionary = steps[i]
		i += 1
		if step.has("if") and not GameState.check(step["if"]):
			continue
		if step.has("t"):
			await _show_line(step)
		if step.has("choice"):
			var target := await _show_choices(step["choice"])
			if target != "":
				steps = DialogueDB.get_dialogue(target)
				i = 0
				continue
		if step.has("do"):
			GameState.run_actions(step["do"])
		if step.has("goto"):
			steps = DialogueDB.get_dialogue(step["goto"])
			i = 0
	root.visible = false
	# Swallow the key press that closed the box so it doesn't also make Kieran jump.
	await get_tree().create_timer(0.12, true).timeout
	active = false
	finished.emit(id)


func _show_line(step: Dictionary) -> void:
	var sp: String = step.get("s", "narrator")
	var tex := DialogueDB.portrait(sp, step.get("p", ""))
	portrait_rect.texture = tex
	portrait_rect.visible = tex != null
	name_label.text = DialogueDB.speaker_name(sp) if sp != "narrator" else ""
	name_label.add_theme_color_override("font_color", DialogueDB.speaker_color(sp))
	var text: String = step["t"]
	if sp == "narrator":
		text = "[i]%s[/i]" % text
	text_label.text = text
	text_label.visible_characters = 0
	choices_box.visible = false
	hint_label.visible = false
	line_shown.emit(sp, step["t"])
	if sp == "piko":
		AudioManager.play_sfx("piko_chirp" if randf() < 0.6 else "piko_trill", 0.08)
	_typing = true
	_advance_requested = false
	var total := text_label.get_total_character_count()
	var shown := 0.0
	var speed := CHARS_PER_SEC * maxf(Settings.text_speed, 0.01)
	var blip_t := 0.0
	while shown < total:
		if Settings.text_speed <= 0.0 or _advance_requested:
			shown = total
			_advance_requested = false
		else:
			var dt := get_process_delta_time()
			shown += speed * dt
			blip_t -= dt
			if blip_t <= 0.0 and sp != "piko" and sp != "narrator":
				AudioManager.play_sfx("blip", 0.06, -6.0)
				blip_t = 0.07
		text_label.visible_characters = int(shown)
		await get_tree().process_frame
	text_label.visible_characters = -1
	_typing = false
	hint_label.visible = true
	_advance_requested = false
	while not _advance_requested:
		await get_tree().process_frame
	_advance_requested = false
	AudioManager.play_sfx("ui_move", 0.0, -8.0)


func _show_choices(options: Array) -> String:
	for c in choices_box.get_children():
		c.queue_free()
	hint_label.visible = false
	choices_box.visible = true
	_choice_made = ""
	var first: Button
	var picked := {"done": false, "goto": "", "do": []}
	for opt in options:
		if opt.has("if") and not GameState.check(opt["if"]):
			continue
		var b := Button.new()
		b.text = opt["t"]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_font_size_override("font_size", int(30 * Settings.text_scale))
		b.pressed.connect(func():
			picked["done"] = true
			picked["goto"] = opt.get("goto", "")
			picked["do"] = opt.get("do", []))
		choices_box.add_child(b)
		if first == null:
			first = b
	if first:
		first.grab_focus()
	while not picked["done"]:
		await get_tree().process_frame
	AudioManager.play_sfx("ui_confirm")
	choices_box.visible = false
	GameState.run_actions(picked["do"])
	return picked["goto"]
