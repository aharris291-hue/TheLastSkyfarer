"""Procedural audio for The Last Skyfarer demo.

Every sound in the demo is synthesised here from scratch (no samples, no
third-party audio), so the project owns it outright. These are temporary
placeholder cues until a composer/sound designer delivers final audio.

Run from the repository root:  python3 -I tools/audio_synth.py
Requires numpy and ffmpeg (for OGG encoding).
"""
import os
import subprocess
import wave

import numpy as np

SR = 44100
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "assets", "audio")
rng = np.random.default_rng(7)


def note(n):
    """MIDI note number -> Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


def env(length, a=0.01, d=0.1, s=0.6, r=0.2):
    n = int(length * SR)
    t = np.arange(n) / SR
    e = np.ones(n) * s
    an, dn, rn = int(a * SR), int(d * SR), int(r * SR)
    if an:
        e[:an] = np.linspace(0, 1, an)
    if dn:
        e[an:an + dn] = np.linspace(1, s, min(dn, max(0, n - an)))[: len(e[an:an + dn])]
    if rn and rn < n:
        e[-rn:] *= np.linspace(1, 0, rn)
    return e


def tone(freq, length, kind="soft", vol=0.3, a=0.01, d=0.15, s=0.5, r=0.3, vib=0.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = freq * (1 + vib * np.sin(2 * np.pi * 5.2 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    if kind == "soft":      # flute/ocarina-ish
        w = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    elif kind == "pluck":   # harp/guitar-ish
        w = np.sin(ph) + 0.5 * np.sin(2 * ph) * np.exp(-t * 6) + 0.3 * np.sin(3 * ph) * np.exp(-t * 9)
    elif kind == "pad":
        w = (np.sin(ph) + 0.5 * np.sin(ph * 1.003) + 0.35 * np.sin(2 * ph * 0.998)
             + 0.15 * np.sin(3 * ph))
    elif kind == "bell":
        w = np.sin(ph) + 0.6 * np.sin(2.76 * ph) * np.exp(-t * 3) + 0.3 * np.sin(5.4 * ph) * np.exp(-t * 6)
    else:
        w = np.sin(ph)
    return w * env(length, a, d, s, r) * vol


def place(buf, sig, at):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def reverb(x, mix=0.3, decays=(0.031, 0.047, 0.061, 0.083), fb=0.55):
    y = np.copy(x)
    for d in decays:
        k = int(d * SR)
        z = np.zeros_like(x)
        for i in range(0, 6):
            off = k * (i + 1)
            if off >= len(x):
                break
            z[off:] += x[:-off] * (fb ** (i + 1))
        y += z * mix / len(decays) * 2
    return y


def lowpass(x, alpha):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


def lowpass_fast(x, alpha, passes=1):
    # vectorised one-pole via exponential smoothing in chunks (approx.)
    from numpy.lib.stride_tricks import sliding_window_view  # noqa: F401
    y = x
    for _ in range(passes):
        k = max(1, int(1 / alpha))
        kernel = np.exp(-np.arange(k * 4) / k)
        kernel /= kernel.sum()
        y = np.convolve(y, kernel, mode="same")
    return y


def normalize(x, peak=0.85):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def save(name, x, loop=False):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.clip(x, -1, 1)
    wav = path.rsplit(".", 1)[0] + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    if path.endswith(".ogg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis",
                        "-q:a", "4", path], check=True)
        os.remove(wav)
    print(name, f"{len(x) / SR:.1f}s")


# ---------------------------------------------------------------------------
# Music
# ---------------------------------------------------------------------------

def windrest_theme():
    """Warm, pastoral village loop in D major pentatonic, 84 bpm, 16 bars."""
    bpm = 84
    beat = 60 / bpm
    bars = 16
    length = bars * 4 * beat
    buf = np.zeros(int(length * SR) + SR * 3)
    # chord roots per bar (D, Bm, G, A) x4 with variation
    prog = [50, 47, 43, 45, 50, 47, 43, 45, 43, 45, 50, 47, 43, 45, 50, 50]
    qual = {50: [0, 4, 7], 47: [0, 3, 7], 43: [0, 4, 7], 45: [0, 4, 7]}
    for b, root in enumerate(prog):
        t0 = b * 4 * beat
        for iv in qual[root]:
            place(buf, tone(note(root + iv), 4 * beat + 0.4, "pad", 0.07, a=0.6, d=0.5, s=0.8, r=0.8), t0)
        place(buf, tone(note(root - 12), 4 * beat, "soft", 0.12, a=0.05, d=0.4, s=0.6, r=0.5), t0)
        # arpeggio plucks
        arp = [0, 7, 12, 16 if qual[root][1] == 4 else 15, 12, 7, 12, 19]
        for k, iv in enumerate(arp):
            place(buf, tone(note(root + 12 + iv), 0.6, "pluck", 0.05, a=0.003, d=0.2, s=0.15, r=0.3),
                  t0 + k * beat / 2)
    # melody (D pentatonic: D E F# A B)
    mel = [
        (74, 1), (76, 0.5), (78, 0.5), (81, 1.5), (78, 0.5), (76, 2), (74, 2),
        (71, 1), (74, 1), (76, 2), (78, 1), (76, 1), (74, 4),
        (78, 1), (81, 1), (83, 1.5), (81, 0.5), (78, 2), (76, 2),
        (74, 1), (76, 1), (78, 1), (76, 1), (74, 4),
        (69, 2), (71, 1), (74, 1), (76, 3), (74, 1),
        (78, 1.5), (76, 0.5), (74, 1), (71, 1), (74, 4),
        (81, 1), (78, 1), (76, 1), (78, 1), (74, 2), (71, 2),
        (74, 2), (76, 1), (78, 1), (74, 4),
    ]
    t = 0.0
    for n, d in mel:
        if t >= length:
            break
        place(buf, tone(note(n), d * beat + 0.15, "soft", 0.11, a=0.04, d=0.2, s=0.7, r=0.25, vib=0.004), t)
        t += d * beat
    x = reverb(buf, 0.35)
    # make the tail wrap around for a seamless loop
    n = int(length * SR)
    tail = x[n:]
    x = x[:n]
    x[: len(tail)] += tail
    save("music/windrest_theme.ogg", normalize(x, 0.7))


def workshop_theme():
    """Quiet, curious, slightly mysterious: sparse bells over a drone (A dorian)."""
    length = 48.0
    buf = np.zeros(int(length * SR) + SR * 4)
    for k, root in enumerate([45, 45, 41, 43, 45, 45, 48, 43]):
        t0 = k * 6
        for iv in (0, 7, 12):
            place(buf, tone(note(root + iv), 6.6, "pad", 0.06, a=1.5, d=1, s=0.8, r=1.5), t0)
    bells = [(69, 0), (72, 1.5), (76, 3), (74, 4.5), (69, 7.5), (67, 9), (72, 12), (76, 13.5),
             (79, 15), (77, 18), (76, 19.5), (72, 21), (69, 24), (71, 27), (72, 28.5), (76, 30),
             (74, 33), (72, 36), (69, 37.5), (67, 39), (69, 42), (76, 45)]
    for n, at in bells:
        place(buf, tone(note(n), 2.5, "bell", 0.06, a=0.002, d=0.6, s=0.2, r=1.5), at)
    x = reverb(buf, 0.5, fb=0.6)
    n = int(length * SR)
    tail = x[n:]
    x = x[:n]
    x[: len(tail)] += tail
    save("music/workshop_theme.ogg", normalize(x, 0.6))


def sky_theme():
    """Soaring, open: wide pads and a rising melody (G lydian), 96 bpm."""
    bpm = 96
    beat = 60 / bpm
    bars = 12
    length = bars * 4 * beat
    buf = np.zeros(int(length * SR) + SR * 3)
    prog = [43, 45, 40, 48, 43, 45, 47, 48, 43, 45, 40, 43]
    for b, root in enumerate(prog):
        t0 = b * 4 * beat
        for iv in (0, 7, 11, 14, 16):
            place(buf, tone(note(root + iv), 4 * beat + 0.5, "pad", 0.05, a=0.4, d=0.4, s=0.8, r=0.8), t0)
        for k in range(8):
            iv = [0, 7, 14, 16, 19, 16, 14, 7][k]
            place(buf, tone(note(root + 12 + iv), 0.5, "pluck", 0.04, a=0.003, d=0.15, s=0.1, r=0.3),
                  t0 + k * beat / 2)
    mel = [(79, 2), (81, 1), (83, 1), (86, 3), (83, 1), (81, 2), (79, 2), (78, 4),
           (79, 1), (81, 1), (83, 2), (86, 2), (88, 2), (86, 4), (83, 2), (81, 2), (79, 4),
           (74, 2), (76, 1), (78, 1), (79, 4), (81, 2), (83, 2), (79, 4)]
    t = 0.0
    for n, d in mel:
        if t >= length:
            break
        place(buf, tone(note(n), d * beat + 0.2, "soft", 0.1, a=0.05, d=0.2, s=0.75, r=0.3, vib=0.006), t)
        t += d * beat
    x = reverb(buf, 0.4)
    n = int(length * SR)
    tail = x[n:]
    x = x[:n]
    x[: len(tail)] += tail
    save("music/sky_theme.ogg", normalize(x, 0.7))


# ---------------------------------------------------------------------------
# Ambience and SFX
# ---------------------------------------------------------------------------

def noise(length):
    return rng.standard_normal(int(length * SR))


def wind_loop():
    length = 20.0
    n = noise(length)
    x = lowpass_fast(n, 1 / 40, passes=2)
    t = np.arange(len(x)) / SR
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * t / length * 3) * np.sin(2 * np.pi * t / length * 2 + 1)
    x = x * gust
    fade = int(SR * 1.0)
    x[:fade] = x[:fade] * np.linspace(0, 1, fade) + x[-fade:] * np.linspace(1, 0, fade)
    x = x[:-fade]
    save("sfx/wind_loop.ogg", normalize(x, 0.5))


def sfx():
    # footstep: short filtered noise thump
    s = lowpass_fast(noise(0.09), 1 / 12) * env(0.09, 0.002, 0.03, 0.2, 0.05)
    save("sfx/step.wav", normalize(s, 0.35))
    # jump: quick upward chirp + cloth
    t = np.arange(int(0.18 * SR)) / SR
    s = np.sin(2 * np.pi * (300 + 900 * t) * t) * np.exp(-t * 14) * 0.5
    s += lowpass_fast(noise(0.18), 1 / 4) * env(0.18, 0.005, 0.05, 0.2, 0.1) * 0.4
    save("sfx/jump.wav", normalize(s, 0.45))
    # land: low thud
    t = np.arange(int(0.2 * SR)) / SR
    s = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 22) + lowpass_fast(noise(0.2), 1 / 10) * np.exp(-t * 25) * 0.6
    save("sfx/land.wav", normalize(s, 0.5))
    # interact: soft wooden tick + bell
    s = tone(note(84), 0.35, "bell", 0.5, a=0.002, d=0.1, s=0.2, r=0.2)
    save("sfx/interact.wav", normalize(s, 0.4))
    # dialogue blip
    s = tone(note(79), 0.05, "soft", 0.5, a=0.002, d=0.02, s=0.5, r=0.02)
    save("sfx/blip.wav", normalize(s, 0.18))
    # quest start: two rising notes
    buf = np.zeros(int(0.9 * SR))
    place(buf, tone(note(74), 0.5, "pluck", 0.5, r=0.3), 0)
    place(buf, tone(note(81), 0.6, "pluck", 0.5, r=0.4), 0.15)
    save("sfx/quest_start.wav", normalize(reverb(buf, 0.3), 0.5))
    # quest complete: arpeggio
    buf = np.zeros(int(1.6 * SR))
    for k, n in enumerate([74, 78, 81, 86]):
        place(buf, tone(note(n), 0.9, "bell", 0.4, a=0.002, d=0.3, s=0.3, r=0.6), k * 0.11)
    save("sfx/quest_complete.wav", normalize(reverb(buf, 0.4), 0.55))
    # Piko chirp: quick warbling sine
    t = np.arange(int(0.28 * SR)) / SR
    f = 1500 + 600 * np.sin(2 * np.pi * 18 * t) + 700 * t
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(0.28, 0.01, 0.08, 0.6, 0.12)
    save("sfx/piko_chirp.wav", normalize(s, 0.35))
    # Piko trill (longer, curious)
    t = np.arange(int(0.55 * SR)) / SR
    f = 1300 + 500 * np.sin(2 * np.pi * 11 * t) * (1 - t) + 900 * t ** 2
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(0.55, 0.02, 0.1, 0.6, 0.2)
    save("sfx/piko_trill.wav", normalize(s, 0.35))
    # glider deploy: cloth whoosh
    n = noise(0.5)
    t = np.arange(len(n)) / SR
    s = lowpass_fast(n, 1 / 6) * np.sin(np.pi * t / 0.5) ** 2
    save("sfx/glide_open.wav", normalize(s, 0.5))
    # gust: swelling filtered noise
    n = noise(1.6)
    t = np.arange(len(n)) / SR
    s = lowpass_fast(n, 1 / 25) * np.sin(np.pi * t / 1.6) ** 1.5
    save("sfx/gust.wav", normalize(s, 0.6))
    # page turn
    n = noise(0.3)
    t = np.arange(len(n)) / SR
    s = (n - lowpass_fast(n, 1 / 3)) * np.exp(-((t - 0.1) ** 2) / 0.004)
    save("sfx/page.wav", normalize(s, 0.35))
    # compass hum / magic: shimmering bells
    buf = np.zeros(int(2.5 * SR))
    for k, n_ in enumerate([81, 88, 93, 86, 91, 96]):
        place(buf, tone(note(n_), 1.6, "bell", 0.3, a=0.01, d=0.5, s=0.3, r=1.0, vib=0.01), k * 0.12)
    save("sfx/compass.wav", normalize(reverb(buf, 0.5), 0.5))
    # discovery / secret
    buf = np.zeros(int(1.4 * SR))
    for k, n_ in enumerate([79, 83, 86, 91]):
        place(buf, tone(note(n_), 0.8, "soft", 0.3, a=0.01, d=0.2, s=0.5, r=0.5), k * 0.09)
    save("sfx/discovery.wav", normalize(reverb(buf, 0.4), 0.5))
    # hidden floor compartment: wooden creak + thunk
    t = np.arange(int(0.9 * SR)) / SR
    creak = np.sin(2 * np.pi * np.cumsum(180 + 60 * np.sin(2 * np.pi * 7 * t)) / SR) * env(0.9, 0.05, 0.3, 0.5, 0.3) * 0.4
    creak += np.sign(np.sin(2 * np.pi * 37 * t)) * 0.05 * env(0.9, 0.05, 0.3, 0.5, 0.3)
    thunk = np.zeros_like(t)
    k0 = int(0.7 * SR)
    tt = t[: len(t) - k0]
    thunk[k0:] = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 18)
    save("sfx/compartment.wav", normalize(lowpass_fast(creak + thunk, 1 / 3), 0.6))
    # UI move / confirm / back
    save("sfx/ui_move.wav", normalize(tone(note(86), 0.06, "soft", 0.5, a=0.002, d=0.02, s=0.4, r=0.03), 0.2))
    save("sfx/ui_confirm.wav", normalize(tone(note(91), 0.15, "bell", 0.5, a=0.002, d=0.05, s=0.3, r=0.1), 0.3))
    save("sfx/ui_back.wav", normalize(tone(note(79), 0.12, "soft", 0.5, a=0.002, d=0.04, s=0.3, r=0.06), 0.25))
    # updraft loop (airy, brighter wind)
    n = noise(4.0)
    hp = n - lowpass_fast(n, 1 / 6)
    x = lowpass_fast(hp, 1 / 3) * 0.8
    fade = int(SR * 0.5)
    x[:fade] = x[:fade] * np.linspace(0, 1, fade) + x[-fade:] * np.linspace(1, 0, fade)
    save("sfx/updraft_loop.wav", normalize(x[:-fade], 0.35))


if __name__ == "__main__":
    windrest_theme()
    workshop_theme()
    sky_theme()
    wind_loop()
    sfx()
