extends MenuBase
## In-game pause menu.

const SlotMenu := preload("res://scripts/ui/slot_menu.gd")
const SettingsMenu := preload("res://scripts/ui/settings_menu.gd")
const JournalMenu := preload("res://scripts/ui/journal_menu.gd")


func _ready() -> void:
	make_backdrop(0.55)
	var b := make_panel(640, "Paused")
	var info := make_label("Chapter %d  ·  %s  ·  %s" % [GameState.chapter, _location(), SaveManager.format_time(GameState.playtime)], 24, Color(0.8, 0.76, 0.68))
	info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	b.add_child(info)
	add_button(b, "Resume", close)
	add_button(b, "Journal & Map", func(): _open(JournalMenu.new()))
	add_button(b, "Save Game", func():
		var m := SlotMenu.new()
		m.mode = "save"
		_open(m))
	add_button(b, "Load Game", func():
		var m := SlotMenu.new()
		m.mode = "load"
		_open(m))
	add_button(b, "Settings", func(): _open(SettingsMenu.new()))
	add_button(b, "Quit to Title", func():
		get_tree().paused = false
		HUD.set_gameplay(false)
		Router.go("res://scenes/ui/title_screen.tscn"))
	focus_first()


func _location() -> String:
	var level := get_tree().get_first_node_in_group("level")
	return level.location_label() if level else ""


func _open(menu: Control) -> void:
	visible = false
	get_parent().add_child(menu)
	menu.tree_exited.connect(func():
		if is_inside_tree():
			visible = true
			focus_first())
