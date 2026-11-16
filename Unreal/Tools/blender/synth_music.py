"""Composes and synthesises the Milestone A music as seamless loops (16-bit mono WAV, 44.1 kHz), with numpy only.
All melodies and harmonies here are original. Instruments are simple synthesis: a plucked string (Karplus-Strong),
a soft bell (FM), a warm pad (detuned partials) and a round bass; a synthetic hall reverb is applied circularly, so
each loop's tail wraps into its start and the loop has no seam.

  music_main_theme "The Last Skyfarer": the Windrest melody, slow and wide, bells over rising arpeggios (title)
  music_windrest   the Windrest theme: morning in the village (plucked strings, pad, bass)
  music_workshop   night in Elias's workshop: sparse bells over a low pad
  music_dawn       the dawn launch and gliding: rising arpeggios, open and airy
  music_fog        where the wind refuses to go: ethereal, no pulse

  blender --background --factory-startup --python synth_music.py -- <output folder> [--preview]
"""
import os
import sys
import wave

import numpy as np

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.getcwd()
os.makedirs(OUT, exist_ok=True)
SR = 44100
rng = np.random.default_rng(7)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def save(name, x, peak=0.7):
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    print("LS_MUSIC_FILE %s %.1fs" % (name, len(x) / SR))


def adsr(n, a, d, s, r):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = int(r * SR)
    if rel > 0 and rel < n:
        e[-rel:] *= np.linspace(1, 0, rel)
    return e


def pluck(freq, dur, bright=0.5):
    """Karplus-Strong plucked string."""
    n = int(dur * SR)
    p = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, p) * bright + rng.uniform(-1, 1, p) * (1 - bright) * 0.3
    periods = []
    for _ in range(n // p + 1):
        # One period at a time (vectorised): average neighbours and lose a little energy, like the classic loop.
        periods.append(buf)
        buf = 0.5 * (buf + np.roll(buf, -1)) * 0.996
    out = np.concatenate(periods)[:n]
    return out * adsr(n, 0.002, 0.6, 0.0, 0.05)


def bell(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * 3.5 * t) * 2.2 * np.exp(-t * 3)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 1.6) * adsr(n, 0.005, 9, 1, 0.05)


def pad(freqs, dur, attack=1.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det, amp in ((0.0, 1.0), (0.004, 0.6), (-0.005, 0.6)):
            ff = f * (1 + det)
            for k, a in ((1, 1.0), (2, 0.35), (3, 0.15)):
                x += amp * a * np.sin(2 * np.pi * ff * k * t + rng.uniform(0, 6.28))
    return x / (len(freqs) * 3) * adsr(n, attack, 4, 0.85, min(1.5, dur / 3))


def bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)) * adsr(n, 0.01, 0.5, 0.55, 0.1)


def reverb_circular(x, seconds=2.6, mix=0.32):
    """Hall reverb from a decaying noise impulse, applied circularly so the loop's tail wraps around."""
    m = int(seconds * SR)
    ir = rng.normal(size=m) * np.exp(-np.arange(m) / (SR * seconds / 5))
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir * ir))
    n = len(x)
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(np.pad(ir, (0, max(0, n - m)))[:n], n), n)
    # gentle lowpass on the wet signal for warmth
    y = np.fft.irfft(np.fft.rfft(y) / (1 + (np.fft.rfftfreq(n, 1 / SR) / 2500) ** 2), n)
    out = x + mix * y * (np.max(np.abs(x)) / (np.max(np.abs(y)) + 1e-9))
    # A gentle overall warmth: soften everything above about 3 kHz, like a felt-damped room.
    return np.fft.irfft(np.fft.rfft(out) / np.sqrt(1 + (np.fft.rfftfreq(n, 1 / SR) / 3000) ** 4), n)


def place(track, sig, t0):
    """Add sig at t0 seconds, wrapping past the end (so notes that ring over the loop point continue at its start)."""
    i0 = int(t0 * SR) % len(track)
    n = len(sig)
    first = min(n, len(track) - i0)
    track[i0:i0 + first] += sig[:first]
    if n > first:
        track[:n - first] += sig[first:]


# D major scale degrees (MIDI); chords as root, third, fifth around middle C.
D = 62
SCALE = [0, 2, 4, 5, 7, 9, 11]


def deg(d, octave=0):
    return D + 12 * (octave + d // 7) + SCALE[d % 7]


# The Windrest theme (original): eight bars of melody in scale degrees, with note lengths in beats.
THEME = [(4, 1), (5, 0.5), (4, 0.5), (2, 1), (0, 1),
         (1, 1.5), (2, 0.5), (4, 2),
         (5, 1), (7, 1), (6, 1), (4, 1),
         (5, 3), (None, 1),
         (4, 1), (5, 0.5), (4, 0.5), (2, 1), (0, 1),
         (1, 1), (2, 1), (3, 1), (5, 1),
         (4, 1.5), (2, 0.5), (1, 1), (-1, 1),
         (0, 3), (None, 1)]
# Chords per bar (scale degree of the root): I vi IV V | I iii IV V
PROGRESSION = [0, 5, 3, 4, 0, 2, 3, 4]


def chord(root_deg):
    return [midi(deg(root_deg, -1)), midi(deg(root_deg + 2, -1)), midi(deg(root_deg + 4, -1))]


def theme_track(bpm, bars_repeat, melody_voice, with_bass=True, with_pluck_arps=False):
    beat = 60.0 / bpm
    bars = 8 * bars_repeat
    track = np.zeros(int(bars * 4 * beat * SR))
    for rep in range(bars_repeat):
        base = rep * 8 * 4 * beat
        for b, root in enumerate(PROGRESSION):
            t0 = base + b * 4 * beat
            place(track, 0.55 * pad(chord(root), 4 * beat + 0.8), t0)
            if with_bass:
                place(track, 0.5 * bass(midi(deg(root, -2)), 2 * beat), t0)
                place(track, 0.35 * bass(midi(deg(root + 4, -2)), 2 * beat), t0 + 2 * beat)
            if with_pluck_arps:
                for k, d in enumerate((0, 2, 4, 2, 7, 4, 2, 4)):
                    place(track, 0.18 * pluck(midi(deg(root + d, 0)), 1.2, 0.4), t0 + k * 0.5 * beat)
        t = base
        for note, length in THEME:
            if note is not None:
                place(track, 0.42 * melody_voice(midi(deg(note, 1 if melody_voice is bell else 0)), length * beat + 0.8), t)
            t += length * beat
    return reverb_circular(track)


def main_theme():
    """The Last Skyfarer main theme: the Windrest melody, slower and wider, carried by bells over rising arpeggios."""
    return theme_track(72, 1, bell, with_bass=True, with_pluck_arps=True)


def windrest():
    return theme_track(84, 2, lambda f, d: pluck(f, d + 0.6, 0.65), with_bass=True)


def excerpt(x, seconds=30.0, fade=3.0):
    """A preview: the first seconds of a loop with a gentle fade-out."""
    n = min(len(x), int(seconds * SR))
    y = x[:n].copy()
    f = int(fade * SR)
    y[-f:] *= np.linspace(1, 0, f)
    return y


if "--preview" in sys.argv:
    save("preview_main_theme", excerpt(main_theme(), 32.0))
    save("preview_windrest_theme", excerpt(windrest(), 32.0))
    print("LS_MUSIC_OK")
    sys.exit(0)

def soft_bell(f, d):
    return 0.55 * bell(f, d)


save("music_main_theme", main_theme())
# Windrest in three moods, switched by the time of day.
save("music_windrest_day", windrest())
save("music_windrest_sunset", theme_track(72, 1, bell, with_bass=True))           # slower, golden, bells over the pad
save("music_windrest_night", theme_track(58, 1, soft_bell, with_bass=False))     # hushed: pad and a soft bell only


# Workshop at night: sparse bells over a low, slowly changing pad (D minor colours), 66 bpm, 12 bars.
def workshop():
    beat = 60.0 / 66
    bars = 12
    track = np.zeros(int(bars * 4 * beat * SR))
    chords = [[50, 57, 62, 65], [46, 53, 58, 62], [48, 55, 60, 64], [45, 52, 57, 61]]   # Dm, Bb, C, A
    for b in range(bars):
        place(track, 0.6 * pad([midi(n) for n in chords[(b // 3) % 4]], 3 * 4 * beat + 1.0, attack=3.0) if b % 3 == 0 else np.zeros(1), b * 4 * beat)
    motif = [(74, 0), (77, 1.5), (76, 3), (72, 6), (74, 9), (69, 12.5), (72, 16), (74, 19), (77, 24), (76, 27), (74, 30), (69, 36), (72, 40)]
    for note, beat_at in motif:
        place(track, 0.32 * bell(midi(note), 4.0), beat_at * beat)
    return reverb_circular(track, 3.4, 0.45)


save("music_workshop_elias", workshop())   # the Elias motif: bittersweet bells over a low pad


# Dawn launch and gliding: rising arpeggios in E major with a lifted fourth, 96 bpm, 16 bars.
def dawn():
    beat = 60.0 / 96
    bars = 16
    track = np.zeros(int(bars * 4 * beat * SR))
    roots = [64, 61, 57, 59]   # E, C#m, A, B
    for b in range(bars):
        r = roots[(b // 2) % 4]
        t0 = b * 4 * beat
        if b % 2 == 0:
            place(track, 0.5 * pad([midi(r - 12), midi(r - 5), midi(r), midi(r + 4)], 8 * beat + 1.0, attack=1.0), t0)
            place(track, 0.45 * bass(midi(r - 24), 3 * beat), t0)
        for k, step in enumerate((0, 7, 12, 16, 19, 16, 12, 7)):
            place(track, 0.16 * pluck(midi(r + step), 0.9, 0.7), t0 + k * 0.5 * beat)
    soar = [(76, 0, 3), (78, 3, 1), (80, 4, 4), (83, 8, 2), (81, 10, 2), (80, 12, 4), (76, 16, 3), (78, 19, 1), (81, 20, 4), (80, 24, 2), (78, 26, 2), (76, 28, 4)]
    for rep in (0, 32):
        for note, at, ln in soar:
            place(track, 0.3 * bell(midi(note), ln * beat + 1.5), (rep + at) * beat)
    return reverb_circular(track, 2.8, 0.38)


save("music_dawn", dawn())


def glide_layer():
    """A layer over the dawn piece (same key and tempo) that the game fades in with glide speed and height."""
    beat = 60.0 / 96
    bars = 16
    track = np.zeros(int(bars * 4 * beat * SR))
    roots = [64, 61, 57, 59]
    for b in range(bars):
        r = roots[(b // 2) % 4]
        for k, step in enumerate((12, 19, 24, 28, 31, 28, 24, 19)):
            place(track, 0.2 * pluck(midi(r + step), 0.7, 0.8), b * 4 * beat + k * 0.5 * beat)
        place(track, 0.12 * bell(midi(r + 24), 2.5), b * 4 * beat)
    return reverb_circular(track, 2.4, 0.4)


save("music_glide_layer", glide_layer())


# The fog: no pulse; slow shimmering clusters that drift between two harmonies, 40 s.
def fog():
    secs = 40.0
    track = np.zeros(int(secs * SR))
    for i, notes in enumerate(([50, 57, 64, 69, 74], [48, 55, 62, 67, 76], [50, 57, 62, 69, 71], [46, 53, 62, 65, 72])):
        place(track, 0.6 * pad([midi(n) for n in notes], 13.0, attack=4.0), i * 10.0)
    for t0 in np.arange(2.0, secs, 3.7):
        place(track, 0.12 * bell(midi(int(rng.choice([81, 83, 86, 88, 90]))), 5.0), float(t0))
    return reverb_circular(track, 4.5, 0.6)


save("music_fog", fog())
print("LS_MUSIC_OK")
