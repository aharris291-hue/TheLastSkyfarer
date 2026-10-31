extends CanvasLayer
## Gameplay HUD (autoload "HUD"): objective tracker, interaction prompt,
## notifications, location banners and tutorial hints.

var _root: Control
var _objective_panel: PanelContainer
var _objective_title: Label
var _objective_text: Label
var _prompt: PanelContainer
var _prompt_label: Label
var _toasts: VBoxContainer
var _banner: VBoxContainer
var _banner_title: Label
var _banner_sub: Label
var _tutorial: PanelContainer
var _tutorial_label: Label
var _tutorial_action := ""
var _tutorial_text := ""
var _prompt_action := ""
var _prompt_text := ""
var gameplay := false


func _ready() -> void:
	layer = 40
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build()
	GameState.notify.connect(_on_notify)
	GameState.quest_changed.connect(func(_q): refresh_objective())
	GameState.objective_changed.connect(func(_q): refresh_objective())
	GameState.flag_changed.connect(func(_f, _v): refresh_objective())
	Settings.changed.connect(_on_settings)
	set_gameplay(false)


func _label(size: int, color := Color(0.97, 0.93, 0.85)) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0.05, 0.04, 0.03))
	l.add_theme_constant_override("outline_size", 6)
	return l


func _build() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)

	_objective_panel = PanelContainer.new()
	_objective_panel.position = Vector2(40, 36)
	_objective_panel.custom_minimum_size = Vector2(520, 0)
	_objective_panel.modulate.a = 0.92
	var ov := VBoxContainer.new()
	_objective_title = _label(24, Color(0.95, 0.8, 0.5))
	_objective_text = _label(28)
	_objective_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_objective_text.custom_minimum_size = Vector2(460, 0)
	ov.add_child(_objective_title)
	ov.add_child(_objective_text)
	_objective_panel.add_child(ov)
	_root.add_child(_objective_panel)

	_toasts = VBoxContainer.new()
	_toasts.anchor_left = 1.0
	_toasts.anchor_right = 1.0
	_toasts.offset_left = -620
	_toasts.offset_right = -40
	_toasts.offset_top = 40
	_toasts.alignment = BoxContainer.ALIGNMENT_BEGIN
	_toasts.add_theme_constant_override("separation", 10)
	_root.add_child(_toasts)

	_prompt = PanelContainer.new()
	_prompt.anchor_left = 0.5
	_prompt.anchor_right = 0.5
	_prompt.anchor_top = 1.0
	_prompt.anchor_bottom = 1.0
	_prompt.offset_top = -170
	_prompt.offset_bottom = -110
	_prompt.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_prompt.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_prompt_label = _label(30)
	_prompt.add_child(_prompt_label)
	_prompt.visible = false
	_root.add_child(_prompt)

	_banner = VBoxContainer.new()
	_banner.anchor_left = 0.5
	_banner.anchor_right = 0.5
	_banner.offset_top = 150
	_banner.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_banner.alignment = BoxContainer.ALIGNMENT_CENTER
	_banner_title = _label(64, Color(1, 0.94, 0.8))
	_banner_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner_sub = _label(30, Color(0.9, 0.85, 0.7))
	_banner_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.add_child(_banner_title)
	_banner.add_child(_banner_sub)
	_banner.modulate.a = 0.0
	_root.add_child(_banner)

	_tutorial = PanelContainer.new()
	_tutorial.anchor_left = 0.5
	_tutorial.anchor_right = 0.5
	_tutorial.anchor_top = 1.0
	_tutorial.anchor_bottom = 1.0
	_tutorial.offset_top = -280
	_tutorial.offset_bottom = -210
	_tutorial.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_tutorial.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_tutorial_label = _label(28, Color(0.85, 0.95, 1.0))
	_tutorial.add_child(_tutorial_label)
	_tutorial.visible = false
	_root.add_child(_tutorial)


func set_gameplay(on: bool) -> void:
	gameplay = on
	_root.visible = on
	if on:
		refresh_objective()


func refresh_objective() -> void:
	var text := GameState.current_objective_text()
	if text == "":
		_objective_panel.visible = false
		return
	_objective_panel.visible = true
	_objective_title.text = GameState.quests_db.get(GameState.tracked_quest, {}).get("title", "").to_upper()
	_objective_text.text = "◆ " + text


func show_prompt(text: String, action := "interact") -> void:
	_prompt_action = action
	_prompt_text = text
	_prompt_label.text = "[%s]  %s" % [Settings.action_label(action), text]
	_prompt.visible = true


func hide_prompt() -> void:
	_prompt.visible = false


func show_tutorial(text: String, action := "") -> void:
	## text may contain {key} which is replaced by the action's binding.
	_tutorial_action = action
	_tutorial_text = text
	_tutorial_label.text = text.replace("{key}", Settings.action_label(action)) if action != "" else text
	_tutorial.visible = true


func hide_tutorial() -> void:
	_tutorial.visible = false
	_tutorial_text = ""


func _on_settings() -> void:
	if _prompt.visible:
		show_prompt(_prompt_text, _prompt_action)
	if _tutorial.visible and _tutorial_text != "":
		show_tutorial(_tutorial_text, _tutorial_action)


func banner(title: String, subtitle := "", hold := 2.6) -> void:
	_banner_title.text = title
	_banner_sub.text = subtitle
	var tw := create_tween()
	tw.tween_property(_banner, "modulate:a", 1.0, 0.8)
	tw.tween_interval(hold)
	tw.tween_property(_banner, "modulate:a", 0.0, 1.0)


func _on_notify(text: String, kind: String) -> void:
	var colors := {
		"quest_start": Color(1.0, 0.85, 0.5), "quest_complete": Color(0.7, 1.0, 0.7),
		"objective": Color(0.85, 0.95, 0.8), "item": Color(0.95, 0.9, 0.75),
		"journal": Color(0.75, 0.88, 1.0), "save": Color(0.8, 0.8, 0.85),
		"discovery": Color(0.9, 0.8, 1.0),
	}
	var icons := {"quest_start": "✦", "quest_complete": "✔", "objective": "✓", "item": "+",
		"journal": "✎", "save": "⟳", "discovery": "★"}
	match kind:
		"quest_start":
			AudioManager.play_sfx("quest_start")
		"quest_complete":
			AudioManager.play_sfx("quest_complete")
		"journal":
			AudioManager.play_sfx("page")
		"discovery":
			AudioManager.play_sfx("discovery")
	var p := PanelContainer.new()
	var l := _label(26, colors.get(kind, Color.WHITE))
	l.text = "%s  %s" % [icons.get(kind, "•"), text]
	p.add_child(l)
	p.modulate.a = 0.0
	_toasts.add_child(p)
	var tw := p.create_tween()
	tw.tween_property(p, "modulate:a", 1.0, 0.3)
	tw.tween_interval(3.2)
	tw.tween_property(p, "modulate:a", 0.0, 0.6)
	tw.tween_callback(p.queue_free)
