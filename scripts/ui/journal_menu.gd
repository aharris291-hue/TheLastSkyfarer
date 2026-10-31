extends MenuBase
## Journal: Quests · Journal (Elias & Piko's notes) · Items · Map.
## Switch tabs with Q/R or LB/RB.

const TABS := ["Quests", "Journal", "Items", "Map"]

var start_tab := 0
var tabs: TabContainer
var _detail_journal: RichTextLabel
var _detail_items: RichTextLabel


func _ready() -> void:
	make_backdrop(0.7)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 70)
	add_child(margin)
	var outer := PanelContainer.new()
	margin.add_child(outer)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	outer.add_child(v)
	var head := HBoxContainer.new()
	head.add_child(make_title("Kieran's Journal", 44))
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(spacer)
	head.add_child(make_label("[%s] / [%s] change tab    [%s] close" % [
		Settings.action_label("tab_prev"), Settings.action_label("tab_next"),
		"Esc" if Settings.last_device == "keyboard" else "B"], 22, Color(0.8, 0.75, 0.65)))
	v.add_child(head)
	tabs = TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.add_theme_font_size_override("font_size", 30)
	v.add_child(tabs)
	_build_quests()
	_build_journal()
	_build_items()
	_build_map()
	tabs.current_tab = start_tab
	tabs.tab_changed.connect(func(_t):
		AudioManager.play_sfx("page")
		focus_first(tabs.get_current_tab_control()))
	AudioManager.play_sfx("page")
	focus_first(tabs.get_current_tab_control())


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("tab_next"):
		tabs.current_tab = (tabs.current_tab + 1) % tabs.get_tab_count()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("tab_prev"):
		tabs.current_tab = (tabs.current_tab - 1 + tabs.get_tab_count()) % tabs.get_tab_count()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("journal") or event.is_action_pressed("map"):
		get_viewport().set_input_as_handled()
		close()
	else:
		super._unhandled_input(event)


func _scroll_page(title: String) -> VBoxContainer:
	var scroll := ScrollContainer.new()
	scroll.name = title
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	tabs.add_child(scroll)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 14)
	scroll.add_child(v)
	return v


func _build_quests() -> void:
	var v := _scroll_page("Quests")
	var ids: Array = GameState.quests.keys()
	ids.sort_custom(func(a, b):
		var sa: String = GameState.quests[a]["state"]
		var sb: String = GameState.quests[b]["state"]
		if sa != sb:
			return sa == "active"
		return GameState.quests_db[a].get("main", false) and not GameState.quests_db[b].get("main", false))
	if ids.is_empty():
		v.add_child(make_label("No quests yet."))
	for qid in ids:
		var def: Dictionary = GameState.quests_db[qid]
		var state: String = GameState.quests[qid]["state"]
		var tag := "MAIN" if def.get("main", false) else "SIDE"
		var title := make_label("%s   %s%s" % [tag, def["title"], "   — Complete" if state == "complete" else ""], 32,
			Color(0.98, 0.86, 0.58) if state == "active" else Color(0.65, 0.8, 0.65))
		title.focus_mode = Control.FOCUS_ALL
		v.add_child(title)
		v.add_child(make_label(def.get("desc", ""), 26, Color(0.85, 0.8, 0.72)))
		for o in def.get("objectives", []):
			if o.has("hidden_until") and not GameState.check(o["hidden_until"]) and state != "complete":
				continue
			var done := GameState.objective_done(qid, o["id"])
			var txt: String = ("✔ " if done else "○ ") + o["text"]
			if o.get("count", 1) > 1 and not done:
				txt += " (%d/%d)" % [GameState.quests[qid]["obj"].get(o["id"], 0), o["count"]]
			v.add_child(make_label("      " + txt, 26, Color(0.7, 0.85, 0.7) if done else Color(0.95, 0.92, 0.85)))
		v.add_child(HSeparator.new())


func _split_page(title: String) -> Array:
	var h := HBoxContainer.new()
	h.name = title
	h.add_theme_constant_override("separation", 24)
	tabs.add_child(h)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(620, 0)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	h.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	var detail := RichTextLabel.new()
	detail.bbcode_enabled = true
	detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail.add_theme_font_size_override("normal_font_size", int(30 * Settings.text_scale))
	detail.add_theme_font_size_override("italics_font_size", int(30 * Settings.text_scale))
	detail.add_theme_font_size_override("bold_font_size", int(34 * Settings.text_scale))
	h.add_child(detail)
	return [list, detail]


func _build_journal() -> void:
	var parts := _split_page("Journal")
	var list: VBoxContainer = parts[0]
	_detail_journal = parts[1]
	var notes := GameState.collectible_count("elias_notes")
	list.add_child(make_label("Elias's notes: %d / %d" % [notes.x, notes.y], 24, Color(0.8, 0.76, 0.68)))
	if GameState.journal.is_empty():
		_detail_journal.text = "Nothing written yet."
	for id in GameState.journal:
		var e: Dictionary = GameState.journal_db[id]
		var prefix: String = {"elias": "✎ ", "piko": "✦ ", "story": "• "}.get(e.get("kind", ""), "• ")
		var b := Button.new()
		b.text = prefix + e["title"]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_font_size_override("font_size", 26)
		b.focus_entered.connect(func(): _show_entry(id))
		b.pressed.connect(func(): _show_entry(id))
		list.add_child(b)
	if not GameState.journal.is_empty():
		_show_entry(GameState.journal[-1])


func _show_entry(id: String) -> void:
	var e: Dictionary = GameState.journal_db[id]
	var kind: String = {"elias": "From Elias's journals", "piko": "Piko's Notes", "story": "Kieran's notes"}.get(e.get("kind", ""), "")
	_detail_journal.text = "[b]%s[/b]\n[i]%s[/i]\n\n%s" % [e["title"], kind, e["text"]]


func _build_items() -> void:
	var parts := _split_page("Items")
	var list: VBoxContainer = parts[0]
	_detail_items = parts[1]
	var order := {"quest": 0, "key": 1, "misc": 2}
	var ids: Array = GameState.inventory.keys()
	ids.sort_custom(func(a, b): return order.get(GameState.items_db.get(a, {}).get("category", "misc"), 3) < order.get(GameState.items_db.get(b, {}).get("category", "misc"), 3))
	if ids.is_empty():
		_detail_items.text = "Kieran's satchel is empty."
	for id in ids:
		var d: Dictionary = GameState.items_db.get(id, {})
		var b := Button.new()
		var cat: String = {"quest": "Delivery", "key": "Key item", "misc": "Misc"}.get(d.get("category", "misc"), "")
		b.text = "%s   (%s)%s" % [d.get("name", id), cat, "  x%d" % GameState.inventory[id] if GameState.inventory[id] > 1 else ""]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_font_size_override("font_size", 26)
		b.focus_entered.connect(func(): _detail_items.text = "[b]%s[/b]\n\n%s" % [d.get("name", id), d.get("desc", "")])
		list.add_child(b)
	if not ids.is_empty():
		var d0: Dictionary = GameState.items_db.get(ids[0], {})
		_detail_items.text = "[b]%s[/b]\n\n%s" % [d0.get("name", ids[0]), d0.get("desc", "")]


func _build_map() -> void:
	var page := Control.new()
	page.name = "Map"
	tabs.add_child(page)
	var map := TextureRect.new()
	map.texture = load("res://assets/ui/windrest_map.jpg")
	map.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	map.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	map.set_anchors_preset(Control.PRESET_FULL_RECT)
	map.focus_mode = Control.FOCUS_ALL
	page.add_child(map)
	var overlay := Control.new()
	overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	page.add_child(overlay)
	var legend := make_label("★ discovered    ◉ you are here    Undiscovered places stay unmarked.", 22, Color(0.95, 0.9, 0.8))
	legend.position = Vector2(10, 0)
	page.add_child(legend)
	await get_tree().process_frame
	await get_tree().process_frame
	# Work out where the image actually sits inside the rect (keep-aspect centred).
	var tex_size := map.texture.get_size()
	var rect_size := map.size
	var sc := minf(rect_size.x / tex_size.x, rect_size.y / tex_size.y)
	var draw_size := tex_size * sc
	var origin := (rect_size - draw_size) * 0.5
	var level := get_tree().get_first_node_in_group("level")
	var here: String = level.current_location if level else ""
	for id in GameState.locations_db.keys():
		var loc: Dictionary = GameState.locations_db[id]
		var known: bool = id in GameState.discovered
		if not known and id != here:
			continue
		var p := origin + Vector2(loc["map"][0], loc["map"][1]) * draw_size
		var mark := make_label("◉" if id == here else "★", 38, Color(0.3, 0.75, 1.0) if id == here else Color(1.0, 0.85, 0.3))
		mark.add_theme_color_override("font_outline_color", Color(0.1, 0.07, 0.04))
		mark.add_theme_constant_override("outline_size", 8)
		mark.position = p - Vector2(14, 26)
		overlay.add_child(mark)
		var name_l := make_label(loc["name"], 22, Color(1, 0.97, 0.9))
		name_l.autowrap_mode = TextServer.AUTOWRAP_OFF
		name_l.add_theme_color_override("font_outline_color", Color(0.1, 0.07, 0.04))
		name_l.add_theme_constant_override("outline_size", 6)
		name_l.position = p + Vector2(22, -18)
		overlay.add_child(name_l)
	if GameState.has_flag("compass_active"):
		var arrow := make_label("→ an impossible wind current", 26, Color(0.6, 0.9, 1.0))
		arrow.autowrap_mode = TextServer.AUTOWRAP_OFF
		arrow.add_theme_color_override("font_outline_color", Color(0.05, 0.1, 0.2))
		arrow.add_theme_constant_override("outline_size", 8)
		arrow.position = origin + Vector2(0.80, 0.42) * draw_size
		overlay.add_child(arrow)
