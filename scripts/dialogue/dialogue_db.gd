extends Node
## Loads every dialogue file in data/dialogue/ (autoload "DialogueDB").
##
## A dialogue is an array of steps. Each step may contain:
##   "s": speaker id, "p": portrait expression, "t": text,
##   "if": condition (see GameState.check), "do": actions (GameState.run_actions),
##   "choice": [{"t": text, "goto": dialogue id, "if": cond, "do": actions}],
##   "goto": dialogue id (jump), "canon": true when quoted from the source docs.

const DIR := "res://data/dialogue"

var dialogues := {}
var speakers := {}


func _ready() -> void:
	speakers = GameState._load_json("res://data/speakers.json")
	var dir := DirAccess.open(DIR)
	if dir == null:
		push_error("No dialogue directory")
		return
	for f in dir.get_files():
		if f.ends_with(".json"):
			var d := GameState._load_json("%s/%s" % [DIR, f])
			for k in d.keys():
				if dialogues.has(k):
					push_error("Duplicate dialogue id %s in %s" % [k, f])
				dialogues[k] = d[k]


func has(id: String) -> bool:
	return dialogues.has(id)


func get_dialogue(id: String) -> Array:
	return dialogues.get(id, [])


func speaker_name(id: String) -> String:
	return speakers.get(id, {}).get("name", id.capitalize())


func portrait(id: String, expr: String) -> Texture2D:
	var sp: Dictionary = speakers.get(id, {})
	var prefix: String = sp.get("portrait", "")
	if prefix == "":
		return null
	var e: String = expr if expr != "" else str(sp.get("default", "neutral"))
	var path := "res://assets/portraits/%s_%s.png" % [prefix, e]
	if not ResourceLoader.exists(path):
		path = "res://assets/portraits/%s_%s.png" % [prefix, sp.get("default", "neutral")]
	if not ResourceLoader.exists(path):
		return null
	return load(path)


func speaker_color(id: String) -> Color:
	return Color(speakers.get(id, {}).get("color", "#f3dfb0"))
