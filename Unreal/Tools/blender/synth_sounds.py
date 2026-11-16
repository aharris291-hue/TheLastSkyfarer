"""Synthesises the Milestone A sound groundwork as 16-bit mono WAVs (44.1 kHz) with numpy only: no recordings, no
downloads. Loops are built in the frequency domain over their whole length, so they repeat without a seam.

  wind_low_loop, wind_high_loop     the core wind, mixed by altitude and speed in game
  glide_rush_loop, glider_flutter_loop
  village_ambience_loop, workshop_tone_loop
  step_grass_1..4, step_stone_1..4, step_wood_1..4
  windmill_creak_1..2, ui_click, ui_hover

Run with Blender's Python (it bundles numpy), or any Python with numpy:
  blender --background --factory-startup --python synth_sounds.py -- <output folder>
"""
import os
import sys
import wave

import numpy as np

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.getcwd()
os.makedirs(OUT, exist_ok=True)
SR = 44100
rng = np.random.default_rng(2026)


def save(name, x, peak=0.8):
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    data = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    print("LS_SOUND " + name)


def shaped_noise(seconds, shape):
    """Periodic noise whose spectrum follows shape(freqs): loops seamlessly."""
    n = int(SR * seconds)
    spec = (rng.normal(size=n // 2 + 1) + 1j * rng.normal(size=n // 2 + 1))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= shape(np.maximum(f, 1.0))
    spec[0] = 0
    return np.fft.irfft(spec, n)


def band(f, lo, hi, slope=2.0):
    return 1 / (1 + (lo / f) ** slope) / (1 + (f / hi) ** slope)


def periodic_lfo(seconds, cycles, depth, seed_phase=0.0):
    """Slow modulation with a whole number of cycles over the loop, so it stays seamless."""
    n = int(SR * seconds)
    t = np.arange(n) / n
    m = np.zeros(n)
    for k, c in enumerate(cycles):
        m += np.sin(2 * np.pi * c * t + seed_phase + k * 1.7) / (k + 1)
    m /= np.max(np.abs(m)) + 1e-9
    return 1 - depth + depth * (0.5 + 0.5 * m)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def onepole_lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


# ------------------------------------------------------------------ wind (the core sound)
L = 12.0
low = shaped_noise(L, lambda f: band(f, 30, 380, 2.0) / f ** 0.5) * periodic_lfo(L, (1, 2, 3), 0.55)
save("wind_low_loop", low, 0.7)

L = 10.0
high = shaped_noise(L, lambda f: band(f, 700, 3200, 2.0)) * periodic_lfo(L, (2, 3, 5), 0.7, 0.8)
# A faint whistle: a narrow band that drifts, built from three periodic partials.
t = np.arange(int(SR * L)) / SR
whistle = sum(np.sin(2 * np.pi * (f0 + 40 * np.sin(2 * np.pi * t * k / L)) * t) for k, f0 in ((1, 1180), (2, 1470), (3, 960)))
high = high + 0.05 * whistle * periodic_lfo(L, (1, 4), 0.9, 2.0)
save("wind_high_loop", high, 0.6)

L = 6.0
save("glide_rush_loop", shaped_noise(L, lambda f: band(f, 900, 7000, 1.5)) * periodic_lfo(L, (3, 7), 0.3), 0.6)

L = 4.0
n = int(SR * L)
t = np.arange(n) / n
flap_rate = 18 + 4 * np.sin(2 * np.pi * 2 * t)                     # flaps per second, wandering
phase = np.cumsum(flap_rate) / SR
flap = (0.5 + 0.5 * np.sin(2 * np.pi * phase * L / L)) ** 3
save("glider_flutter_loop", shaped_noise(L, lambda f: band(f, 180, 1600, 2.0)) * (0.25 + 0.75 * flap), 0.6)

# ------------------------------------------------------------------ village and workshop beds
L = 24.0
n = int(SR * L)
bed = 0.35 * shaped_noise(L, lambda f: band(f, 60, 900, 1.5) / f ** 0.3) * periodic_lfo(L, (1, 2), 0.5)
bed += 0.12 * shaped_noise(L, lambda f: band(f, 2500, 9000, 2.0)) * periodic_lfo(L, (3, 5, 7), 0.9, 1.1)   # leaves
for _ in range(18):   # birds: little frequency-swept chirps, two or three in a phrase
    start = rng.uniform(0.2, L - 1.0)
    base = rng.uniform(2400, 4200)
    for k in range(int(rng.integers(2, 4))):
        dur = rng.uniform(0.06, 0.14)
        m = int(SR * dur)
        tt = np.arange(m) / SR
        sweep = base * (1 + rng.uniform(-0.25, 0.35) * tt / dur)
        chirp = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.sin(np.pi * tt / dur) ** 2
        i0 = int(SR * (start + k * rng.uniform(0.12, 0.22)))
        if i0 + m < n:
            bed[i0:i0 + m] += 0.18 * chirp
save("village_ambience_loop", bed, 0.5)

L = 12.0
n = int(SR * L)
room = shaped_noise(L, lambda f: band(f, 25, 220, 2.0) / f ** 0.5)
room += 0.03 * np.sin(2 * np.pi * 50 * np.arange(n) / SR)            # a soft lantern hum
for _ in range(10):                                                     # lantern crackle
    i0 = int(rng.uniform(0, n - 2000))
    room[i0:i0 + 600] += rng.normal(size=600) * env(600, 0.0005, 0.004) * 0.05
save("workshop_tone_loop", room, 0.35)


# ------------------------------------------------------------------ footsteps
def step(kind, i):
    m = int(SR * 0.22)
    tt = np.arange(m) / SR
    noise = rng.normal(size=m)
    if kind == "grass":
        x = np.convolve(noise, [1, -0.85], "same") * env(m, 0.004, 0.05)        # brushy, bright crunch
        x += 0.4 * onepole_lowpass(rng.normal(size=m), 400) * env(m, 0.002, 0.03)
    elif kind == "stone":
        x = 0.8 * np.convolve(noise, [1, -0.95], "same") * env(m, 0.0005, 0.012)  # sharp scuff
        x += 0.9 * np.sin(2 * np.pi * rng.uniform(110, 150) * tt) * env(m, 0.001, 0.025)
    else:  # wood: hollow knock with a short ring
        f0 = rng.uniform(170, 230)
        x = np.sin(2 * np.pi * f0 * tt) * env(m, 0.001, 0.06) + 0.5 * np.sin(2 * np.pi * f0 * 2.7 * tt) * env(m, 0.001, 0.03)
        x += 0.3 * onepole_lowpass(noise, 2000) * env(m, 0.0005, 0.01)
    save("step_%s_%d" % (kind, i), x * rng.uniform(0.85, 1.0), 0.7)


for kind in ("grass", "stone", "wood"):
    for i in range(1, 5):
        step(kind, i)

# ------------------------------------------------------------------ windmill creak (stick-slip pulses through wood resonances)
for i in (1, 2):
    secs = 1.8 + 0.4 * i
    m = int(SR * secs)
    x = np.zeros(m)
    tcur = 0.05
    rate = rng.uniform(40, 70)
    while tcur < secs - 0.1:
        j = int(tcur * SR)
        x[j] = rng.uniform(0.5, 1.0)
        rate *= rng.uniform(0.97, 1.04)
        tcur += 1 / rate
    for f0, q in ((520, 0.996), (880, 0.994), (1350, 0.99)):   # simple resonators
        y = np.zeros(m)
        w = 2 * np.pi * f0 / SR
        y1 = y2 = 0.0
        for k in range(m):
            y0 = x[k] + 2 * q * np.cos(w) * y1 - q * q * y2
            y[k] = y0
            y2, y1 = y1, y0
        x = x + 0.4 * y / (np.max(np.abs(y)) + 1e-9)
    x *= np.sin(np.pi * np.arange(m) / m) ** 0.5
    save("windmill_creak_%d" % i, x, 0.6)

# ------------------------------------------------------------------ UI
m = int(SR * 0.08)
tt = np.arange(m) / SR
save("ui_click", (np.sin(2 * np.pi * 1250 * tt) + 0.4 * np.sin(2 * np.pi * 2500 * tt)) * env(m, 0.001, 0.018), 0.5)
m = int(SR * 0.06)
tt = np.arange(m) / SR
save("ui_hover", np.sin(2 * np.pi * 880 * tt) * env(m, 0.004, 0.02), 0.3)
# ------------------------------------------------------------------ sound pass 2: Piko, compass, journal, map, stingers, gusts, glider
def fm_chirp(f0, f1, dur, mod_ratio=2.0, mod_depth=1.5):
    m = int(SR * dur)
    tt = np.arange(m) / SR
    f = np.geomspace(f0, f1, m)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase + mod_depth * np.sin(phase * mod_ratio) * np.exp(-tt * 8)) * np.sin(np.pi * tt / dur) ** 1.5


# Piko (non-verbal): quick bright chirps and warbling trills, small and friendly.
for i, (a, b, d) in enumerate(((1800, 2900, 0.12), (2600, 1900, 0.1), (2000, 3400, 0.16), (3000, 2400, 0.09)), 1):
    x = fm_chirp(a, b, d, 2.0, 1.2)
    if i % 2 == 0:
        x = np.concatenate([x, np.zeros(int(SR * 0.04)), 0.7 * fm_chirp(b, a * 1.1, d * 0.8, 2.0, 1.0)])
    save("piko_chirp_%d" % i, x, 0.5)
for i in (1, 2):
    parts = []
    for k in range(7 + i * 2):
        f = 2200 + 500 * np.sin(k * 0.9 + i) + rng.uniform(-80, 80)
        parts.append(fm_chirp(f, f * 1.15, 0.055, 2.0, 0.8))
        parts.append(np.zeros(int(SR * 0.012)))
    save("piko_trill_%d" % i, np.concatenate(parts) * np.linspace(0.8, 1.0, sum(len(p) for p in parts)), 0.5)


def brass_shimmer(base, dur, rise=1.0):
    m = int(SR * dur)
    tt = np.arange(m) / SR
    x = np.zeros(m)
    for k, ratio in enumerate((1.0, 2.76, 5.4, 8.93)):   # inharmonic partials: a struck brass ring
        x += np.sin(2 * np.pi * base * ratio * (1 + (rise - 1) * tt / dur) * tt) * np.exp(-tt * (2.5 + k * 1.5)) / (k + 1)
    air = shaped_noise(dur, lambda f: band(f, 2000, 9000, 2.0))[:m] * env(m, 0.15, 0.5) * 0.25
    return x + air


save("compass_pulse", brass_shimmer(660, 1.6, 1.03), 0.55)
awaken = brass_shimmer(440, 3.5, 1.12)
echo = np.pad(brass_shimmer(880, 2.5, 1.05), (int(SR * 0.6), 0))
echo = np.pad(echo, (0, max(0, len(awaken) - len(echo))))[:len(awaken)]
save("compass_awaken", awaken + 0.6 * echo, 0.6)


def paper(dur, crinkle=30):
    m = int(SR * dur)
    x = np.zeros(m)
    for _ in range(crinkle):   # many small dry crackles, the sound of handled paper
        i0 = int(rng.uniform(0, m - 800))
        x[i0:i0 + 800] += rng.normal(size=800) * env(800, 0.0005, rng.uniform(0.002, 0.006)) * rng.uniform(0.3, 1.0)
    swish = shaped_noise(dur, lambda f: band(f, 1500, 7000, 1.5))[:m] * np.sin(np.pi * np.arange(m) / m) ** 2 * 0.3
    return np.convolve(x, [1, -0.6], "same") + swish


save("journal_page", paper(0.55, 26), 0.5)
m = int(SR * 0.6)
scratch = np.convolve(rng.normal(size=m), [1, -0.9], "same") * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * np.arange(m) / SR) ** 2) * env(m, 0.02, 0.25)
save("journal_ink", scratch, 0.35)
save("map_open", paper(0.8, 40), 0.55)
save("map_close", paper(0.45, 18), 0.45)


def bell_tone(freq, dur):
    m = int(SR * dur)
    tt = np.arange(m) / SR
    return np.sin(2 * np.pi * freq * tt + 1.6 * np.sin(2 * np.pi * freq * 3.5 * tt) * np.exp(-tt * 4)) * np.exp(-tt * 2.2) * env(m, 0.004, 9)


def stinger(notes, gap, tail=1.6):
    m = int(SR * (gap * len(notes) + tail))
    x = np.zeros(m)
    for k, n in enumerate(notes):
        tone = bell_tone(440 * 2 ** ((n - 69) / 12), tail)
        i0 = int(SR * gap * k)
        x[i0:i0 + len(tone)] += tone[:m - i0]
    return x


save("stinger_discovery", stinger([74, 78, 81, 86], 0.13), 0.5)        # D major arpeggio, up: a new place
save("stinger_quest_start", stinger([69, 74], 0.18), 0.45)
save("stinger_quest_done", stinger([74, 78, 81, 79, 86], 0.15, 2.2), 0.5)
save("stinger_journal", stinger([81, 86], 0.1, 1.2), 0.35)

# Wind gusts: swells of the high layer that the game drops in now and then, more often up high.
for i in (1, 2, 3):
    d = 2.5 + i * 0.7
    m = int(SR * d)
    g = shaped_noise(d, lambda f: band(f, 500 + i * 150, 3500, 2.0))[:m] * np.sin(np.pi * np.arange(m) / m) ** 2
    save("wind_gust_%d" % i, g, 0.6)

m = int(SR * 0.7)
save("glider_deploy", shaped_noise(0.7, lambda f: band(f, 300, 4000, 1.5))[:m] * env(m, 0.04, 0.2)
     + 0.8 * np.convolve(rng.normal(size=m), [1, -0.8], "same") * env(m, 0.001, 0.03), 0.6)   # whoosh and a cloth snap
m = int(SR * 0.5)
save("glider_land", np.sin(2 * np.pi * 90 * np.arange(m) / SR) * env(m, 0.002, 0.08)
     + 0.5 * shaped_noise(0.5, lambda f: band(f, 200, 2500, 1.5))[:m] * env(m, 0.005, 0.12), 0.6)
print("LS_SOUNDS_OK")
