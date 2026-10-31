extends Node
## Music, ambience and sound-effect playback (autoload "AudioManager").
## Music crossfades between tracks; SFX use a small voice pool.

const MUSIC := {
	"windrest": "res://assets/audio/music/windrest_theme.ogg",
	"workshop": "res://assets/audio/music/workshop_theme.ogg",
	"sky": "res://assets/audio/music/sky_theme.ogg",
}
const AMBIENCE := {
	"wind": "res://assets/audio/sfx/wind_loop.ogg",
}
const SFX_DIR := "res://assets/audio/sfx/%s.wav"
const VOICES := 10

var _music_a: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _ambience: AudioStreamPlayer
var _voices: Array[AudioStreamPlayer] = []
var _cache := {}
var current_music := ""
var current_ambience := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_music_a = _make_player("Music")
	_music_b = _make_player("Music")
	_ambience = _make_player("Ambience")
	for i in VOICES:
		_voices.append(_make_player("SFX"))


func _make_player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func _stream(path: String) -> AudioStream:
	if not _cache.has(path):
		if not ResourceLoader.exists(path):
			return null
		var s: AudioStream = load(path)
		if s is AudioStreamOggVorbis:
			s.loop = true
		elif s is AudioStreamWAV and path.ends_with("_loop.wav"):
			s.loop_mode = AudioStreamWAV.LOOP_FORWARD
			s.loop_end = int(s.get_length() * s.mix_rate)
		_cache[path] = s
	return _cache[path]


func play_music(track: String, fade := 1.5) -> void:
	if track == current_music:
		return
	current_music = track
	var old := _music_a if _music_a.playing else _music_b
	var new := _music_b if old == _music_a else _music_a
	if old.playing:
		var tw := create_tween()
		tw.tween_property(old, "volume_db", -40.0, fade)
		tw.tween_callback(old.stop)
	if track == "" or not MUSIC.has(track):
		return
	new.stream = _stream(MUSIC[track])
	new.volume_db = -40.0
	new.play()
	var tw2 := create_tween()
	tw2.tween_property(new, "volume_db", 0.0, fade)


func play_ambience(name_: String, volume_db := 0.0) -> void:
	if name_ == current_ambience:
		return
	current_ambience = name_
	if name_ == "" or not AMBIENCE.has(name_):
		_ambience.stop()
		return
	_ambience.stream = _stream(AMBIENCE[name_])
	_ambience.volume_db = volume_db
	_ambience.play()


func play_sfx(name_: String, pitch_jitter := 0.0, volume_db := 0.0) -> void:
	var s := _stream(SFX_DIR % name_)
	if s == null:
		push_warning("Missing sfx %s" % name_)
		return
	for v in _voices:
		if not v.playing:
			v.stream = s
			v.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
			v.volume_db = volume_db
			v.play()
			return
