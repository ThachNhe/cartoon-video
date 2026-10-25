"""Quicksort in 16 seconds, cut to a 120 BPM track (Shorts/Reels only).

Eight bars are sorted in place (Lomuto partition, pivot = last item) and every step starts on the
grid. The first sweep runs at 1x, one step a beat, to teach the idea; then the video kicks into 2x
(half a beat a step) and the track goes double time with it. Each compared bar plays its own note,
swaps take off with a swish and land with a clack. Bit rides each pivot into its final spot, then
hops to the next one. The last part builds up into a drop on SORTED, and the video is 8 bars long,
so the rewind at the end loops straight back into the first frame, in time and in key.

Render:   BIT_FORMAT=vertical .venv/bin/manim -qh -r 1080,1920 --fps 60 quick_sort.py QuickSort
Preview:  BIT_FORMAT=vertical .venv/bin/manim -ql --fps 30 quick_sort.py QuickSort
Cover:    BIT_FORMAT=vertical .venv/bin/manim -s -r 1080,1920 -o Thumbnail_vertical quick_sort.py Thumbnail
"""

from bitbybit import *
from bitbybit import _env, _save, _sweep, _t_axis

# Pivot 4 splits it into [3, 1, 2] (two one-item parts: the gag) and [8, 6, 5, 7].
VALUES = [5, 8, 3, 7, 1, 6, 2, 4]
CODE = """def quicksort(a, lo, hi):
    if lo >= hi: return
    pivot, i = a[hi], lo
    for j in range(lo, hi):
        if a[j] <= pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]  # FINAL
    quicksort(a, lo, i - 1)
    quicksort(a, i + 1, hi)"""
# The lines of CODE the highlight visits.
LINE = {"base": 1, "pivot": 2, "test": 4, "swap": 5, "place": 7, "left": 8, "right": 9}
STEPS = 21  # 13 compares + 4 pivot landings + 4 one-item parts, for the STEP counter
FIRST_LINE = ("Smaller than 4 goes LEFT", "Smaller than four goes left.")

# 120 BPM: a beat is 15 frames at 30fps. Steps land on eighths and sixteenths; their sounds are put on the
# exact grid even when manim rounds the step to a whole frame.
BPM = 120
BEAT = 60 / BPM
LENGTH = 32  # beats: 8 bars, so the loop comes back in time and on the same chord
CHORDS = ["A", "F", "C", "G"]  # Am F C G, two beats each: 4 rounds in the video
BASS_HZ = {"A": 110.0, "F": 87.31, "C": 130.81, "G": 98.0}
PAD_HZ = {"A": (220.0, 261.63, 329.63), "F": (174.61, 220.0, 261.63), "C": (196.0, 261.63, 329.63),
          "G": (196.0, 246.94, 293.66)}
# A minor pentatonic: the note of values 1..8.
NOTE_HZ = [440.0, 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66]
BEAT_SFX = ("kick", "clap", "hat", "rewind", "swish", "clack", "thud", "ohat", "snare", "riser", "cymbal",
            *[f"bass_{c}" for c in BASS_HZ], *[f"pad_{c}" for c in PAD_HZ],
            *[f"note_{v}" for v in range(1, len(NOTE_HZ) + 1)])

FINAL_GREEN = "#4CD97B"
LEFT_CYAN = "#80DEEA"
MISS_RED = "#FF6B6B"
STYLES = {  # bar state: (fill, stroke, number)
    "idle": ("#262A52", "#6A70C0", TEXT_LIGHT),
    "pivot": (HEADLINE, WHITE, INK),
    "left": (LEFT_CYAN, WHITE, INK),
    "final": (FINAL_GREEN, WHITE, INK),
}
# The code highlight takes the colour of what its line does to the bars.
LINE_COLORS = {"base": FINAL_GREEN, "pivot": HEADLINE, "test": MISS_RED, "swap": LEFT_CYAN, "place": FINAL_GREEN,
               "left": ACCENT, "right": ACCENT}

# Layout of the 8 x 14.2 frame, top to bottom; the bottom quarter (y < -3.55) stays clear for the app's buttons
# (only the code window's bottom padding dips into it). The watermark sits in the bottom-right corner.
HEADER_Y, ROW_Y = 5.55, 5.05
PANEL_TOP = 4.75
SLOT, BAR_W, UNIT = 0.88, 0.7, 0.26  # UNIT: bar height per value; Bit riding the 7 still fits in the panel
BASE_Y = 1.7
CAPTION_Y = BASE_Y - 0.97
PANEL_BOTTOM = BASE_Y - 1.32
CODE_TOP, CODE_BOTTOM = PANEL_BOTTOM - 0.45, -3.65
HEADLINE_Y, BUTTON_Y = -0.55, -1.8
# Everything but the build-up is mixed this much lower, so the build has headroom to swell without clipping.
MIX_TRIM = -5
TOUCHDOWN = 0.5  # swapped bars land halfway through their step: on the offbeat at 1x, a sixteenth later at 2x


def make_beat_sfx():
    """Synthesize the track (drums, bass, pads, riser) and the bars' sounds into assets/sfx/."""
    rng = np.random.default_rng(11)

    t = _t_axis(0.35)
    kick = np.sin(2 * np.pi * np.cumsum(45 + 105 * np.exp(-t * 28)) / SR) * np.exp(-t * 9)
    kick[:60] += rng.normal(size=60) * np.exp(-np.arange(60) / 12) * 0.4  # beater click
    _save("kick", kick, 0.8)

    t = _t_axis(0.07)
    _save("hat", np.diff(rng.normal(size=t.size + 1)) * np.exp(-t * 70), 0.18)

    # Clap: three quick bursts of band-passed noise and a short tail.
    t = _t_axis(0.25)
    noise = rng.normal(size=t.size)
    band = np.convolve(noise, np.ones(4) / 4, "same") - np.convolve(noise, np.ones(24) / 24, "same")
    bursts = sum(np.where(t >= d, np.exp(-np.maximum(t - d, 0) * 220), 0) for d in (0.0, 0.011, 0.022))
    _save("clap", band * (bursts + 0.5 * np.exp(-t * 18)), 0.4)

    # Rolling bass: short plucks, three to a beat (between the kicks).
    for chord, hz in BASS_HZ.items():
        t = _t_axis(0.11)
        tone = sum(np.sin(2 * np.pi * hz * k * t) / k for k in (1, 2, 3))
        _save(f"bass_{chord}", _env(np.tanh(1.5 * tone), attack=0.004, decay_power=1.5), 0.4)

    for v, hz in enumerate(NOTE_HZ, start=1):
        t = _t_axis(0.5)
        tone = np.sin(2 * np.pi * hz * t) + 0.35 * np.sin(2 * np.pi * hz * 4 * t) * np.exp(-t * 30)
        _save(f"note_{v}", tone * np.exp(-t * 8) * np.minimum(1, t / 0.002), 0.35)

    rewind = _sweep(300, 2400, 0.45, wobble=0.3, wobble_hz=22) + rng.normal(size=int(SR * 0.45)) * 0.25
    _save("rewind", _env(rewind, attack=0.05, decay_power=0.6), 0.3)

    # Swaps: an airy swish as the bars take off, a woodblock clack as they land (a heavier thud for the pivot).
    t = _t_axis(0.16)
    air = np.convolve(np.diff(rng.normal(size=t.size + 1)), np.ones(3) / 3, "same")
    _save("swish", air * np.sin(np.pi * t / t[-1]) ** 2 * np.linspace(0.4, 1, t.size), 0.3)
    t = _t_axis(0.12)
    wood = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for a, f, d in ((1, 1250, 55), (0.5, 2600, 80), (0.6, 180, 35)))
    wood[:40] += rng.normal(size=40) * np.exp(-np.arange(40) / 6) * 0.8
    _save("clack", wood, 0.6)
    t = _t_axis(0.3)
    thud = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 12)
    thud[:wood.size] += wood * 0.5
    _save("thud", thud, 0.8)

    # The build and the drop: open hat, snare for the roll, a rising sweep and a cymbal.
    t = _t_axis(0.16)
    _save("ohat", np.diff(rng.normal(size=t.size + 1)) * np.exp(-t * 22), 0.16)
    t = _t_axis(0.18)
    _save("snare", rng.normal(size=t.size) * np.exp(-t * 25) + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.8, 0.45)
    t = _t_axis(1.5)
    rise = _sweep(200, 2200, 1.5) * 0.3 + np.diff(rng.normal(size=t.size + 1)) * 0.6
    _save("riser", rise * (t / t[-1]) ** 2, 0.3)
    t = _t_axis(1.6)
    _save("cymbal", np.diff(np.diff(rng.normal(size=t.size + 2))) * np.exp(-t * 2.8), 0.3)

    # Chord pads, two beats long, ducking under every kick (the "pumping" of dance tracks).
    for chord, notes in PAD_HZ.items():
        t = _t_axis(2 * BEAT)
        tone = sum(np.sin(2 * np.pi * f * d * k * t) / k ** 1.5 for f in notes for d in (0.997, 1.003) for k in range(1, 7))
        pump = np.minimum(1, (t % BEAT) / 0.2) ** 0.7
        _save(f"pad_{chord}", tone * pump * np.minimum(1, (t[-1] - t) / 0.05), 0.3)


def snap(t):
    """Move fast on the beat, then hold: motion is over by 60% of the step."""
    return rate_functions.ease_out_cubic(min(1.0, t / 0.6))


def touchdown(at):
    """Rate for a swap: a smooth throw that lands at fraction `at` of the step, then holds."""
    return lambda t: smooth(min(1.0, t / at))


def over(dx):
    """path_arc that carries a mobject moving by dx over the top (-dx: under)."""
    return -PI / 2 if dx > 0 else PI / 2


def slot_x(k):
    return (k - (len(VALUES) - 1) / 2) * SLOT


def top_of(k, value):
    return np.array([slot_x(k), BASE_Y + value * UNIT, 0])


def paint(bar):
    fill, stroke, ink = STYLES[bar.state]
    alpha = 0.3 if bar.dim else 1.0
    bar[0].set_fill(fill, alpha).set_stroke(stroke, 3, alpha)
    bar[1].set_fill(ink, alpha)
    return bar


class QuickSort(BitScene):
    code_width = 7.3
    narrated = False  # music and on-screen lines only for now; True brings Bit's (cached) voice back

    # ---------------------------------------------------------------- beat grid
    def tick(self, *anims, beats=1, bit_free=True):
        """Play `anims` from this beat to the next one (or `beats` on), to the exact frame.

        manim rounds every play up to whole frames, so each play aims at its beat's absolute frame
        instead of adding run times. Bit bobs on the beat, or talks while his line plays, unless busy.
        """
        if bit_free:
            talking = self.time < self.talk_end - 0.15
            anims += (self.bit.talk(beats * BEAT) if talking else self.bob(),)
        due = [anim for steps, anim in self.queued if steps == 0]
        self.queued = [(steps - 1, anim) for steps, anim in self.queued if steps]
        anims += tuple(due)
        self.b += beats
        fps = config.frame_rate
        frames = round(self.b * BEAT * fps) - round(self.time * fps)
        self.play(*(anims or (Wait(frozen_frame=False),)), run_time=frames / fps - 1e-4)
        assert round(self.time * fps) == round(self.b * BEAT * fps), "fell off the beat grid"

    def after(self, steps, anim):
        """Play `anim` with the step `steps` steps from now (0: the next one)."""
        self.queued.append((steps, anim))

    def sfx(self, name, offset=0.0, gain=None):
        """Sound effects start on the beat grid, not on the frame manim rounded the step to."""
        super().sfx(name, offset + self.b * BEAT - self.time, (gain or 0) + MIX_TRIM)

    def lay_groove(self):
        """The track under the whole video, laid last once its sections are known, sixteenth by sixteenth.

        Intro (kick, offbeat hats); 1x groove (clap, offbeat bass); a snare fill into 2x, which goes
        double time (sixteenth hats with open hats, rolling bass, pumping pads); a build into the SORTED
        drop (kick, bass and pads out, a snare roll and a riser); then the drop (cymbal, louder pads).
        Ducked under Bit's voice when he speaks.
        """
        def put(name, t, gain, trim=MIX_TRIM):
            duck = -6 if any(s - 0.1 < t < e for s, e in self.speech) else 0
            self.add_sound(str(SFX / f"{name}.wav"), time_offset=t - self.time, gain=gain + duck + trim)

        build, fast = self.build_at, self.fast_at
        put("riser", (self.drop_at - 3) * BEAT, 4, trim=0)  # 1.5 s: it peaks on the drop
        put("cymbal", fast * BEAT, -8)
        put("cymbal", self.drop_at * BEAT, -3)
        for q in range(round(self.b * 4)):
            b, pos = q / 4, q % 4  # the beat, and the sixteenth within it
            t, chord = b * BEAT, CHORDS[int(b // 2) % 4]
            intro, double = b < self.intro_end, b >= fast
            building, dropped = build <= b < self.drop_at, b >= self.drop_at
            if double:
                put("ohat" if pos == 2 else "hat", t, -9 if pos == 2 else (-8 if pos == 0 else -13))
            elif pos == 2:
                put("hat", t, -8)
            if building:
                put("snare", t, -6 + 7 * (b - build) / (self.drop_at - build), trim=0)  # the roll swells into the drop
                continue
            if fast - 1 <= b < fast:
                put("snare", t, -12 + 2 * pos)  # a one-beat fill into 2x
            if pos == 0:
                put("kick", t, -2)
            if intro:
                continue
            if pos == 0 and int(b) % 2:
                put("clap", t, -6)
            if pos == 2 or (double and pos):
                put(f"bass_{chord}", t, -6 if pos == 2 else -10)
            if double and pos == 0 and int(b) % 2 == 0:
                put(f"pad_{chord}", t, -9 if dropped else -13)

    def bob(self):
        """Bit squashes on the kick."""
        return self.bit.animate(rate_func=lambda t: there_and_back(min(1.0, t / 0.45))).stretch(0.9, 1, about_edge=DOWN)

    def speak(self, speech):
        if not self.narrated:
            return
        spoken = self.voice(speech, captioned=True)
        self.speech.append((self.time, self.time + spoken))
        self.talk_end = self.time + spoken

    def line(self, caption, speech=None, **colors):
        """Bit says `speech` (default: `caption`) while the status line under the bars shows `caption`."""
        self.speak(speech or caption)
        return self.caption(caption, **colors)

    def caption(self, text, **colors):
        """Replace the status line under the bars; returns the animations."""
        self.close_caption()
        new = Text(text, font=FONT, weight=BOLD, font_size=34, color=TEXT_LIGHT, t2c=colors or None)
        if new.width > 7.0:
            new.scale_to_fit_width(7.0)
        old, self.cap = self.cap, new.move_to([0, CAPTION_Y, 0])
        self.cap_since = (self.time, text)
        # The old line is gone before the new one shows: crossfaded words in one spot turn to mush.
        return [FadeOut(old, shift=UP * 0.25, rate_func=lambda t: min(1.0, t / 0.2)),
                FadeIn(new, scale=0.8, rate_func=lambda t: snap(max(0.0, t - 0.2) / 0.8))]

    def close_caption(self):
        if self.cap_since:
            t, text = self.cap_since
            self.events.append({"t": round(t, 2), "kind": "text", "label": text, "duration": round(self.time - t, 2),
                                "words": len(text.split())})
            self.cap_since = None

    # ---------------------------------------------------------------- pieces
    def watermark(self):
        # This Short keeps the top of the frame for its title bar: the mark goes to the bottom-right corner.
        return super().watermark().to_corner(DR, buff=0.35)

    def background(self):
        """Deep navy with a faint dot grid, like graph paper. Oversized so moves never show an edge."""
        sky = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, fill_color=BG, fill_opacity=1,
                        stroke_width=0)
        dots = VGroup(*[Dot([x, y, 0], radius=0.014, color=WHITE, fill_opacity=0.12)
                        for x in np.arange(-4.75, 4.8, 0.5) for y in np.arange(-7.75, 7.8, 0.5)])
        return Group(sky, flatten(dots))

    def make_bar(self, value, k):
        rect = RoundedRectangle(width=BAR_W, height=value * UNIT, corner_radius=0.06)
        rect.move_to([slot_x(k), BASE_Y, 0], aligned_edge=DOWN)
        number = Text(str(value), font=MONO, weight=BOLD, font_size=20).move_to(rect.get_bottom() + UP * 0.13)
        bar = VGroup(rect, number)
        bar.value, bar.home, bar.state, bar.dim = value, k, "idle", False
        return paint(bar)

    def chip(self, text, color=TEXT_LIGHT, dot=None):
        label = Text(text, font=MONO, weight=BOLD, font_size=22, color=color)
        parts = VGroup(Dot(radius=0.07, color=dot), label).arrange(RIGHT, buff=0.15) if dot else VGroup(label)
        box = RoundedRectangle(width=parts.width + 0.45, height=0.52, corner_radius=0.08, fill_color=BG,
                               fill_opacity=1, stroke_color=color, stroke_width=2)
        return VGroup(box, parts.move_to(box))

    def depth_meter(self, depth):
        squares = VGroup(*[Square(0.2, stroke_color=TEXT_MUTED, stroke_width=2,
                                  fill_color=ACCENT, fill_opacity=1 if k < depth else 0) for k in range(3)])
        meter = VGroup(Text("IN PLACE · DEPTH", font=MONO, font_size=20, color=TEXT_MUTED),
                       squares.arrange(RIGHT, buff=0.08)).arrange(RIGHT, buff=0.2)
        return meter.move_to([-3.75, ROW_Y, 0], aligned_edge=LEFT)

    def replace(self, name, new):
        """Swap a status widget on the spot: it changes on the beat, with no fade."""
        self.remove(getattr(self, name))
        setattr(self, name, new)
        self.add(new)

    def set_step(self, n):
        self.replace("step_chip", self.chip(f"STEP {n}/{STEPS}").move_to([3.75, HEADER_Y, 0], aligned_edge=RIGHT))

    def set_progress(self, n):
        """The panel's top edge fills up green, step by step."""
        w = 7.5 - 0.3
        bar = Line([-w / 2, PANEL_TOP, 0], [-w / 2 + w * max(n, 0.01) / STEPS, PANEL_TOP, 0], stroke_color=FINAL_GREEN,
                   stroke_width=6, stroke_opacity=1 if n else 0)
        self.replace("progress", bar)

    def step(self):
        self.steps += 1
        self.set_step(self.steps)
        self.set_progress(self.steps)

    def set_speed(self, speed):
        """The playback-speed chip, left of the phase chip (kept clear of its widest state)."""
        color = ACCENT if speed > 1 else TEXT_MUTED
        widest = self.chip("PARTITIONING", dot=ACCENT).width
        self.replace("speed_chip", self.chip(f"{speed}×", color).move_to([3.75 - widest - 0.2, ROW_Y, 0],
                                                                           aligned_edge=RIGHT))

    def set_phase(self, text, color):
        self.replace("phase_chip", self.chip(text, color, dot=color).move_to([3.75, ROW_Y, 0], aligned_edge=RIGHT))

    def set_depth(self, depth):
        self.replace("depth", self.depth_meter(depth))

    def ring(self, bar, color=WHITE):
        """An outline bursting off `bar`: the visible hit of a step."""
        ring = bar[0].copy().set_fill(opacity=0).set_stroke(color, 6, 1)
        return ring.animate(remover=True, rate_func=rate_functions.ease_out_cubic).scale(1.3).set_stroke(opacity=0)

    def restyle(self, bar, state=None, dim=None, shift=ORIGIN, arc=0.0, rate=snap):
        """Animate `bar` to a new state (colour) and/or position in one go."""
        bar.state = state or bar.state
        bar.dim = bar.dim if dim is None else dim
        bar.generate_target()
        paint(bar.target).shift(shift)
        return MoveToTarget(bar, path_arc=arc, rate_func=rate)

    def impact(self, bar, at, color=WHITE):
        """A ring bursting where `bar` (already given its target) touches down, at fraction `at` of the step."""
        base = bar.target[0].copy().set_fill(opacity=0)
        ring = base.copy().set_stroke(color, 6, 0)

        def burst(m, alpha):
            x = (alpha - at) / (1 - at)
            if x >= 0:
                e = rate_functions.ease_out_cubic(x)
                m.become(base.copy().scale(1 + 0.35 * e).set_stroke(color, 6, 1 - e))

        return UpdateFromAlphaFunc(ring, burst, remover=True)

    def swap(self, k, to, pace, state=None, pivot=False):
        """bars[k] flies over the top into slot `to` (with Bit on it, if it is the pivot) as the bar there passes under.

        Both take off on the step with a swish and touch down with a clack (the pivot: a thud).
        """
        at = TOUCHDOWN
        dx, bar, other = (to - k) * SLOT, self.bars[k], self.bars[to]
        self.sfx("swish", gain=-3)
        self.sfx("thud" if pivot else "clack", offset=at * pace * BEAT, gain=-1)
        self.bring_to_front(bar, self.bit)
        self.bars[to], self.bars[k] = bar, other
        anims = [self.restyle(bar, state, shift=RIGHT * dx, arc=over(dx), rate=touchdown(at)),
                 self.restyle(other, shift=LEFT * dx, arc=-over(dx), rate=touchdown(at))]
        anims += [self.impact(bar, at, HEADLINE if pivot else WHITE), self.impact(other, at)]
        if pivot:
            anims.append(self.bit.animate(path_arc=over(dx), rate_func=touchdown(at)).shift(RIGHT * dx))
        return anims

    def guide(self, lo, hi):
        """Dashed line at the pivot's height across its part: every bar below it goes left."""
        y = BASE_Y + self.bars[hi].value * UNIT
        return DashedLine([slot_x(lo) - BAR_W / 2 - 0.1, y, 0], [slot_x(hi) - BAR_W / 2, y, 0], dash_length=0.1,
                          stroke_color=HEADLINE, stroke_width=3, stroke_opacity=0.9)

    def show_guide(self, lo, hi):
        """Put up the guide of a new part (under Bit); returns its fade in."""
        self.guide_line = self.guide(lo, hi)
        self.add(self.guide_line)
        self.bring_to_front(self.bit)
        return FadeIn(self.guide_line, rate_func=snap)

    def goto(self, line):
        """Move the code highlight to LINE[line], in that line's colour."""
        return self.cbar.animate(rate_func=snap).set_y(self.code.code_lines[LINE[line]].get_y()).set_fill(
            LINE_COLORS[line], 0.25)

    def hop_to(self, k):
        """Bit jumps onto the bar in slot k."""
        target = self.bit.get_center() + top_of(k, self.bars[k].value) - self.bit.get_bottom()
        self.sfx("pop", gain=-4)
        return self.bit.animate(path_arc=over(target[0] - self.bit.get_x()),
                                rate_func=lambda t: smooth(min(1.0, t / 0.7))).move_to(target)

    def look_left(self, bit):
        for pupil, eye in zip(bit.pupils, bit.eyes):
            pupil.move_to(eye.get_center() + LEFT * 0.09 * bit.unit)
        return bit

    # ---------------------------------------------------------------- timeline
    def construct(self):
        if any(not (SFX / f"{name}.wav").exists() for name in SFX_NAMES):
            make_sfx()
        if any(not (SFX / f"{name}.wav").exists() for name in BEAT_SFX):
            make_beat_sfx()
        self.camera.background_color = BG
        self.stage()
        self.b, self.steps, self.speech, self.talk_end, self.queued = 0, 0, [], 0.0, []
        self.cap, self.cap_since = VGroup(), None

        self.first_frame()
        self.chapter("partition", "One sweep: smaller goes left")
        self.moment("hook")   # the bars, Bit on the pivot and the rule are all up on the first frame
        self.moment("topic")  # QUICKSORT is the title on the first frame
        # Two beats of groove first: Bit bobs on the pivot, then the sweep starts.
        self.tick()
        self.tick()
        self.intro_end = self.b
        self.speak(FIRST_LINE[1])
        p = self.partition(0, 7, pace=1, landing=("4 lands. FINAL spot!", "Four lands. Final spot!"))
        self.moment("reveal")
        self.land(p)
        self.split(p)

        # Now the viewer knows the trick: the rest runs at 2x, on the next bar, and the track goes double time.
        self.chapter("repeat", "Repeat on each side, at 2x")
        self.start(0, 2, "left", self.speed_up())
        p = self.partition(0, 2, pace=0.5)
        self.land(p, beats=0.5)
        self.one_item()
        self.start(4, 7, "right")
        p = self.partition(4, 7, pace=0.5)
        self.build_at = self.b  # the last part plays over the build-up
        self.land(p, p + 1, beats=0.5, cheer=False)  # 7, and the 8 alone on its right
        self.start(4, 5, "left")
        p = self.partition(4, 5, pace=0.5)
        self.chapter("sorted", "Sorted: pick, split, repeat")
        self.sorted_wave(p)
        assert self.steps == STEPS, f"{self.steps} steps, the counter says {STEPS}"
        self.chapter("outro", "Subscribe")
        self.subscribe()
        self.rewind()
        assert self.b == LENGTH, f"{self.b} beats, the loop needs {LENGTH}"
        self.close_caption()
        self.lay_groove()

    def first_frame(self):
        """Everything on screen at 0s: the bars, Bit on the pivot, the code and the rule (also the loop's last frame)."""
        panel = RoundedRectangle(width=7.5, height=PANEL_TOP - PANEL_BOTTOM, corner_radius=0.15, fill_color="#161935",
                                 fill_opacity=0.92, stroke_color="#3A3F75", stroke_width=2)
        panel.move_to([0, (PANEL_TOP + PANEL_BOTTOM) / 2, 0])
        base = Line([-3.55, BASE_Y, 0], [3.55, BASE_Y, 0], stroke_color="#3A3F75", stroke_width=2)
        labels = VGroup(*[Text(f"a[{k}]", font=MONO, font_size=20, color=TEXT_MUTED).move_to([slot_x(k), BASE_Y - 0.25, 0])
                          for k in range(len(VALUES))])
        self.bars = [self.make_bar(v, k) for k, v in enumerate(VALUES)]
        self.bars[-1].state = "pivot"
        paint(self.bars[-1])

        self.code = self.make_code(CODE)
        if self.code.height > CODE_TOP - CODE_BOTTOM:
            self.code.scale_to_fit_height(CODE_TOP - CODE_BOTTOM)
        self.code.move_to([0, CODE_TOP, 0], aligned_edge=UP)
        # The colour key sits in the code window's title bar, right of the window buttons.
        legend = VGroup(*[
            VGroup(Square(0.16, fill_color=color, fill_opacity=1, stroke_width=0),
                   Text(name, font=MONO, font_size=17, color=TEXT_MUTED)).arrange(RIGHT, buff=0.1)
            for name, color in (("FINAL", FINAL_GREEN), ("PIVOT", HEADLINE), ("≤ PIVOT", LEFT_CYAN))
        ]).arrange(RIGHT, buff=0.3)
        legend.move_to(self.code.background.get_corner(UR) + np.array([-0.2, -0.22, 0]), aligned_edge=RIGHT)
        self.code_panel = VGroup(self.shadow(self.code.background), self.code, legend)
        self.cbar = self.line_bar(self.code, LINE["pivot"], color=LINE_COLORS["pivot"]).set_fill(opacity=0.25)
        self.pointer = Triangle(fill_color=ACCENT, fill_opacity=1, stroke_width=0).scale(0.1)
        self.pointer.move_to([slot_x(0), BASE_Y - 0.55, 0])

        title = Text("QUICKSORT", font=FONT, weight=BOLD, font_size=54, color=HEADLINE)
        self.add(panel, base, labels, *self.bars, title.move_to([-3.75, HEADER_Y, 0], aligned_edge=LEFT),
                 self.code_panel, self.cbar, self.pointer)
        self.step_chip = self.phase_chip = self.depth = self.progress = self.speed_chip = VGroup()
        self.set_step(0)
        self.set_speed(1)
        self.set_progress(0)
        self.set_phase("PARTITIONING", ACCENT)
        self.set_depth(1)
        self.caption(FIRST_LINE[0], LEFT=LEFT_CYAN)
        self.add(self.cap)  # already up on the first frame, no fade in

        self.bit = self.look_left(Bit().scale(0.42))
        self.bit.brows.become(self.bit.make_brows("raised"))
        self.add(self.stand(self.bit, top_of(len(VALUES) - 1, VALUES[-1])))
        self.guide_line = self.guide(0, len(VALUES) - 1)
        self.add(self.guide_line)
        self.bring_to_front(self.bit)

    def compare(self, j, i, pivot, pace):
        """One step of the sweep: is a[j] <= pivot? If so it swaps into the left part (slot i).

        At 1x a badge spells the verdict ("≤ 4" / "> 4") over the bar, where it ends up.
        """
        bar = self.bars[j]
        small = bar.value <= pivot
        self.sfx(f"note_{bar.value}", gain=-2)
        self.step()
        anims = [self.pointer.animate(rate_func=snap).set_x(slot_x(j))]
        if pace >= 1:
            badge = Text(f"{'≤' if small else '>'} {pivot}", font=MONO, weight=BOLD, font_size=24,
                         color=LEFT_CYAN if small else MISS_RED)
            badge.move_to(top_of(i if small else j, bar.value) + UP * 0.25).set_opacity(0)
            anims.append(badge.animate(rate_func=there_and_back_with_pause, remover=True).set_opacity(1).shift(UP * 0.15))
        if not small:
            return anims + [self.ring(bar, MISS_RED), self.goto("test")]
        anims += [self.ring(bar, LEFT_CYAN), self.goto("swap")]
        if i == j:
            return anims + [self.restyle(bar, "left")]
        return anims + self.swap(j, i, pace, "left")

    def partition(self, lo, hi, pace, ride_beats=None, landing=None):
        """Sweep lo..hi-1, one step every `pace` beats, then the pivot (with Bit on it) swaps into its slot.

        `landing` is the (caption, speech) shown as the pivot flies. Returns the pivot's final slot.
        """
        pivot, i = self.bars[hi].value, lo
        for j in range(lo, hi):
            small = self.bars[j].value <= pivot
            self.tick(*self.compare(j, i, pivot, pace), beats=pace)
            i += small
        ride = ride_beats or pace
        anims = [self.goto("place"), FadeOut(self.guide_line, rate_func=snap)]
        if i != hi:
            anims += self.swap(hi, i, ride, pivot=True)
        if landing:
            anims += self.line(*landing, FINAL=FINAL_GREEN)
        self.tick(*anims, beats=ride, bit_free=False)
        return i

    def finals(self, *slots):
        """Lock bars as FINAL (pivots that landed, one-item parts); returns the animations."""
        self.sfx("ding", gain=-4)
        anims = []
        for k in slots:
            self.step()
            anims += [self.restyle(self.bars[k], "final", dim=False), self.ring(self.bars[k], FINAL_GREEN)]
        return anims

    def land(self, *slots, beats=1, cheer=True):
        """The pivot (and any one-item part beside it) locks: FINAL, forever. Bit cheers on it."""
        cheers = [self.bit.arms_up(), self.bit.express("grin", "raised")] if cheer else []
        self.tick(*self.finals(*slots), *cheers, beats=beats, bit_free=not cheer)

    def split(self, p):
        """Show the two sides the pivot left behind."""
        sides = VGroup()
        for lo, hi, text, color in ((0, p - 1, f"≤ {self.bars[p].value}", LEFT_CYAN),
                                    (p + 1, len(VALUES) - 1, f"> {self.bars[p].value}", MISS_RED)):
            y = PANEL_TOP - 0.35
            bracket = Line([slot_x(lo) - BAR_W / 2, y - 0.25, 0], [slot_x(hi) + BAR_W / 2, y - 0.25, 0],
                           stroke_color=color, stroke_width=4)
            sides.add(VGroup(bracket, Text(text, font=MONO, weight=BOLD, font_size=26, color=color).move_to([bracket.get_x(), y, 0])))
        self.sides = sides
        self.sfx("pop", gain=-6)
        self.tick(*[GrowFromCenter(s, rate_func=snap) for s in sides], self.bit.arms_rest(),
                  self.bit.express("smile", "neutral"), bit_free=False)

    def start(self, lo, hi, side, extra=()):
        """A new part (the recursive call on the `side` of the last pivot): its bars go back to unsorted,
        the rest dims, and Bit hops onto its pivot. `extra` animations play along."""
        anims = [self.hop_to(hi), self.goto(side), self.pointer.animate(rate_func=snap).set_x(slot_x(lo)),
                 self.show_guide(lo, hi), *extra]
        for k, bar in enumerate(self.bars):
            if bar.state != "final":
                anims.append(self.restyle(bar, "pivot" if k == hi else "idle", dim=not lo <= k <= hi))
        if getattr(self, "sides", None):
            anims += [FadeOut(self.sides, rate_func=snap)]
            self.sides = None
        self.set_depth(2)
        self.tick(*anims, beats=0.5, bit_free=False)

    def one_item(self):
        """The gag: Bit jumps in to sort a one-item part, and it's done before he lands."""
        self.moment("gag")
        self.tick(self.hop_to(0), *self.finals(0), self.goto("base"), *self.line("1 item? Sorted!", "One item? Sorted!"),
                  beats=0.5, bit_free=False)
        self.tick(*self.finals(2), self.bit.arms_rest(), self.bit.express("flat", "raised"), self.bit.look(ORIGIN),
                  beats=0.5, bit_free=False)

    def speed_up(self):
        """The switch to 2x, on a downbeat: a "2× SPEED" banner flashes over the bars and the chip turns to 2×.

        Returns the animations for the step it starts on.
        """
        assert self.b % 4 == 0, "2x starts on a downbeat"
        self.fast_at = self.b
        self.set_speed(2)
        banner = headline_text("2× SPEED", 64, ACCENT).move_to([0, PANEL_TOP - 0.55, 0])  # above Bit and the bars
        self.after(1, FadeOut(banner, scale=1.2, rate_func=snap))
        self.sfx("whoosh", gain=-4)
        return [FadeIn(banner, scale=1.6, rate_func=snap), *self.line("Now 2× speed!", "Now, two times speed!")]

    def sorted_wave(self, p):
        """The drop: the last pivot and its neighbour lock, the bars ripple up the scale, the takeaway lands."""
        self.moment("payoff")
        self.drop_at = self.b
        assert self.b % 4 == 0, "the drop lands on a downbeat"
        self.set_phase("SORTED", FINAL_GREEN)
        self.tick(*self.finals(p, p + 1), FadeOut(self.code_panel, shift=DOWN * 0.3, rate_func=snap),
                  FadeOut(self.cbar, rate_func=snap), FadeOut(self.pointer, rate_func=snap),
                  *self.caption("SORTED!", **{"SORTED!": FINAL_GREEN}), self.confetti(VGroup(*self.bars), count=50),
                  self.bit.arms_up(), self.bit.express("grin", "raised"), beats=2, bit_free=False)

        words = VGroup(*[Text(w, font=FONT, weight=BOLD, font_size=44, color=c) for w, c in
                         (("Pick a pivot.", HEADLINE), ("Split.", LEFT_CYAN), ("Repeat.", FINAL_GREEN))])
        words.arrange(RIGHT, buff=0.25).move_to([0, HEADLINE_Y, 0])
        if words.width > 7.3:
            words.scale_to_fit_width(7.3)
        self.headline = words
        self.speak("Pick a pivot. Split. Repeat.")
        self.log("text", "Pick a pivot. Split. Repeat.", 9 * BEAT, words=5)  # on screen until the rewind
        # Two bars a beat, in eighths, each playing its note: a run up the scale. Bit rides his bar's bounce.
        for pair in range(len(VALUES) // 2):
            anims = []
            for half in range(2):
                k = 2 * pair + half
                self.sfx(f"note_{k + 1}", offset=half * BEAT / 2, gain=-1)

                def rise(t, start=half / 2):
                    return there_and_back(min(1.0, max(0.0, (t - start) / 0.5)))

                mob = Group(self.bars[k], self.bit) if k == p else self.bars[k]
                anims.append(mob.animate(rate_func=rise).shift(UP * 0.35))
            if pair % 2 == 0:
                self.sfx("clap", gain=-6)
                anims.append(FadeIn(words[pair // 2], scale=1.4, rate_func=snap))
            self.tick(*anims, bit_free=False)
        self.sfx("clap", gain=-6)
        self.sfx("boing", gain=-8)
        self.tick(FadeIn(words[2], scale=1.4, rate_func=snap), *[self.ring(b, FINAL_GREEN) for b in self.bars],
                  self.bit.animate(rate_func=lambda t: there_and_back(min(1.0, t / 0.6))).shift(UP * 0.6),
                  bit_free=False)

    def subscribe(self):
        self.moment("cta")
        self.button = self.subscribe_button().scale(0.9).move_to([0, BUTTON_Y, 0])
        self.sfx("pop")
        self.tick(FadeIn(self.button, shift=UP * 0.4, rate_func=snap), *self.line("Subscribe for more!"),
                  self.bit.arms_rest(), self.bit.look(DOWN), bit_free=False)
        self.tick(self.pulse(self.button, times=1))

        done, check = self.subscribe_button(subscribed=True)
        Group(done, check).scale(0.9).move_to(self.button)
        ripple = Circle(radius=0.12, stroke_color=WHITE, stroke_width=5).move_to(self.button.get_center() + DR * 0.2)
        self.done = VGroup(done[1], check)
        self.sfx("pop")
        self.sfx("ding", offset=0.1)
        self.tick(Transform(self.button[0], done[0], rate_func=snap), self.button[1].animate(rate_func=snap).set_opacity(0),
                  FadeIn(done[1], scale=1.2, rate_func=snap), Create(check, rate_func=snap),
                  ripple.animate(remover=True).scale(4).set_stroke(opacity=0), self.confetti(self.button),
                  self.bit.arms_up(), self.bit.express("grin", "raised"), self.bit.look(ORIGIN), beats=1.5, bit_free=False)
        # Back to the first frame's face, so the rewind only has to move Bit.
        self.tick(self.bit.arms_rest(), self.bit.express("smile", "raised"), self.bit.look(LEFT), beats=0.5,
                  bit_free=False)

    def rewind(self):
        """The loop: every bar flies home, Bit rides the pivot back, and the code and rule return as on the first frame."""
        self.moment("loop")
        self.sfx("rewind")
        anims = []
        for bar in self.bars:
            dx = slot_x(bar.home) - bar.get_x()
            anims.append(self.restyle(bar, "pivot" if bar.home == len(VALUES) - 1 else "idle", dim=False,
                                      shift=RIGHT * dx, arc=PI / 3 if abs(dx) > 0.01 else 0.0))
        self.bars.sort(key=lambda bar: bar.home)
        target = self.bit.get_center() + top_of(len(VALUES) - 1, VALUES[-1]) - self.bit.get_bottom()
        anims.append(self.bit.animate(rate_func=snap).move_to(target))
        anims += [FadeOut(m, rate_func=snap) for m in (self.headline, self.button, self.done)]
        self.cbar.set_y(self.code.code_lines[LINE["pivot"]].get_y()).set_fill(LINE_COLORS["pivot"], 0.25)
        self.pointer.set_x(slot_x(0))
        anims += [FadeIn(m, rate_func=snap) for m in (self.code_panel, self.cbar, self.pointer)]
        anims += self.caption(FIRST_LINE[0], LEFT=LEFT_CYAN)
        self.cap_since = None  # the replay carries this line on: it was logged once, from 0s
        anims.append(self.show_guide(0, len(VALUES) - 1))
        self.steps = 0
        self.set_step(0)
        self.set_speed(1)
        self.set_progress(0)
        self.set_phase("PARTITIONING", ACCENT)
        self.set_depth(1)
        # The video ends as the bars land; the replay's two opening beats are the pause before the sweep.
        self.tick(*anims, bit_free=False)


class Thumbnail(ThumbnailMixin, QuickSort):
    def design(self):
        """Shorts/Reels cover: QUICKSORT in big letters over the bars, Bit cheering on the pivot that just landed."""
        values = [1, 2, 3, 4, 8, 6, 5, 7]
        bars = []
        for k, v in enumerate(values):
            bar = self.make_bar(v, k)
            bar.state = "final" if k < 3 else ("pivot" if v == 4 else "idle")
            bars.append(paint(bar))
        VGroup(*bars).scale(1.15).move_to([0, -1.4, 0])
        bit = Bit().scale(0.55)
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("raised"))
        bit.pose_arms(155, 155)
        self.stand(bit, bars[3][0].get_top() + UP * 0.05)
        words = VGroup(headline_text("QUICK", 150, ACCENT), headline_text("SORT", 150, TEXT_LIGHT),
                       headline_text("in 16 seconds", 64, HEADLINE)).arrange(DOWN, buff=0.1)
        words.scale_to_fit_width(7.0).move_to(UP * 3.6)
        self.add(*bars, bit, words)
