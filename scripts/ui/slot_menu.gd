extends MenuBase
## Save / load slot picker. mode = "save" or "load".

var mode := "load"
var _list: VBoxContainer
var _confirm_slot := ""


func _ready() -> void:
	make_backdrop(0.6)
	var b := make_panel(900, "Save Game" if mode == "save" else "Load Game")
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 12)
	b.add_child(_list)
	add_button(b, "Back", close)
	_refresh()


func _refresh() -> void:
	for c in _list.get_children():
		c.queue_free()
	var slots: Array = SaveManager.SLOTS.duplicate()
	if mode == "load":
		slots.push_front(SaveManager.AUTO)
	for s in slots:
		var meta := SaveManager.slot_meta(s)
		var label := ""
		var name_ := "Autosave" if s == SaveManager.AUTO else "Slot %s" % s.substr(4)
		if meta.is_empty():
			label = "%s  —  Empty" % name_
		else:
			label = "%s  —  Ch. %d · %s · %s" % [name_, int(meta.get("chapter", 1)), meta.get("location", ""),
				SaveManager.format_time(float(meta.get("playtime", 0)))]
			if meta.get("recovered", false):
				label += "  (recovered backup)"
		var btn := add_button(_list, label, func(): _pick(s), mode == "load" and meta.is_empty())
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		if not meta.is_empty():
			btn.tooltip_text = str(meta.get("saved_at", ""))
	focus_first(_list)


func _pick(slot: String) -> void:
	if mode == "save":
		if SaveManager.has_save(slot) and _confirm_slot != slot:
			_confirm_slot = slot
			GameState.notify.emit("Press again to overwrite this slot", "save")
			return
		if SaveManager.save_game(slot):
			GameState.notify.emit("Game saved", "save")
		else:
			GameState.notify.emit("Save failed: %s" % SaveManager.last_error, "save")
		_confirm_slot = ""
		_refresh()
	else:
		get_tree().paused = false
		if not SaveManager.load_game(slot):
			GameState.notify.emit("Could not load: %s" % SaveManager.last_error, "save")
