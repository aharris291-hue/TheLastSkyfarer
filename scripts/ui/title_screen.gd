extends MenuBase
## Title screen: key art from the project files, New Game / Continue / Load /
## Settings / Quit.

const SlotMenu := preload("res://scripts/ui/slot_menu.gd")
const SettingsMenu := preload("res://scripts/ui/settings_menu.gd")

var _menu: VBoxContainer


func _ready() -> void:
	get_tree().paused = false
	HUD.set_gameplay(false)
	var art := TextureRect.new()
	art.texture = load("res://assets/ui/title_keyart.jpg")
	art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	art.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(art)
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.02, 0.03, 0.08, 0.35)
	add_child(shade)
	var col := VBoxContainer.new()
	col.anchor_left = 0.56
	col.anchor_right = 0.96
	col.anchor_top = 0.08
	col.anchor_bottom = 0.95
	col.add_theme_constant_override("separation", 14)
	add_child(col)
	var title := make_title("The Last Skyfarer", 96)
	title.add_theme_color_override("font_outline_color", Color(0.08, 0.05, 0.03))
	title.add_theme_constant_override("outline_size", 14)
	col.add_child(title)
	var sub := make_label("A Windrest Village demo", 32, Color(0.95, 0.9, 0.8))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub.add_theme_color_override("font_outline_color", Color(0.08, 0.05, 0.03))
	sub.add_theme_constant_override("outline_size", 8)
	col.add_child(sub)
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 280)
	col.add_child(gap)
	_menu = VBoxContainer.new()
	_menu.add_theme_constant_override("separation", 12)
	_menu.custom_minimum_size = Vector2(460, 0)
	_menu.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(_menu)
	var latest := SaveManager.latest_slot()
	if latest != "":
		add_button(_menu, "Continue", func(): SaveManager.load_game(latest))
	add_button(_menu, "New Game", _new_game)
	add_button(_menu, "Load Game", func():
		var m := SlotMenu.new()
		m.mode = "load"
		_open(m), not SaveManager.any_save())
	add_button(_menu, "Settings", func(): _open(SettingsMenu.new()))
	add_button(_menu, "Quit", func(): get_tree().quit())
	var foot := make_label("v%s  ·  Keyboard or controller" % ProjectSettings.get_setting("application/config/version"), 22, Color(0.9, 0.9, 0.9, 0.8))
	foot.anchor_top = 1.0
	foot.anchor_bottom = 1.0
	foot.offset_top = -50
	foot.offset_left = 30
	add_child(foot)
	AudioManager.play_music("windrest")
	AudioManager.play_ambience("wind", -10.0)
	focus_first(_menu)


func _new_game() -> void:
	GameState.reset()
	Router.go("res://scenes/world/windrest.tscn")


func _open(menu: Control) -> void:
	_menu.visible = false
	add_child(menu)
	menu.tree_exited.connect(func():
		if is_inside_tree():
			_menu.visible = true
			focus_first(_menu))


func on_back() -> void:
	pass
