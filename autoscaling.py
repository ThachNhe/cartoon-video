"""Autoscaling in 20 seconds, timed to a 120 BPM grid (Shorts/Reels only: sound effects and on-screen lines, no narration).

A live dashboard: users send requests (glowing packets) through a load balancer to a row of servers, each
with its CPU meter; a chart tracks the average CPU and the autoscaler's policy runs as code, its highlight
on the line that fires. A traffic spike melts the one server; "cpu > 70" boots three more, one every two
beats, and the build-up drops as the load is shared. At night "cpu < 30" switches them off again, until the
gag: it tries to remove the last one, and max(1, ...) keeps it. The video is 10 bars long and rewinds to its
first frame, so the replay loops in time (and in key, with the beat track on).

The beat track (drums, bass and pads from Quicksort's make_beat_sfx()) is off for now: `music = False`.
The server sounds are synthesized by make_scale_sfx(). Icons are Material Design Icons (assets/icons/, Pictogrammers Free License).

Render:   BIT_FORMAT=vertical .venv/bin/manim -qh -r 1440,2560 --fps 30 autoscaling.py AutoScaling
Preview:  BIT_FORMAT=vertical .venv/bin/manim -ql --fps 30 autoscaling.py AutoScaling
Cover:    BIT_FORMAT=vertical .venv/bin/manim -s -r 1080,1920 -o Thumbnail_vertical autoscaling.py Thumbnail
"""

from scipy import signal

from bitbybit import *
from bitbybit import _save, _t_axis
from quick_sort import BEAT, BEAT_SFX, CHORDS, MIX_TRIM, make_beat_sfx, snap

ICONS = ROOT / "assets" / "icons"
LENGTH = 40  # beats: 10 bars, five rounds of the chords, so the loop comes back in time and on the same chord

CODE = """def autoscale(cpu, n):
    if cpu > 70: n += 1  # scale out
    if cpu < 30: n -= 1  # scale in
    return max(1, min(n, 4))  # 1..4"""
LINE = {"def": 0, "out": 1, "in": 2, "clamp": 3}  # the lines of CODE the highlight visits
FIRST_LINE = ("1 server. Can it keep up?", {"1 server.": ACCENT})

CARD, CARD_EDGE = "#262A52", "#3A3F75"
OK_GREEN, WARN, HOT, COOL = "#4CD97B", "#FFB74D", "#FF5252", "#64B5F6"
PACKET = "#7FDBFF"
BLUE_T, PURPLE_T = ["#5EC8FF", "#1E7FE0"], ["#C3A6FF", "#7C4DFF"]
GRAY_T, RED_T = ["#8A90B8", "#4E547E"], ["#FF8A80", "#D32F2F"]
USER_COLORS = ["#80DEEA", "#A5D6A7", "#FFF59D", "#FFAB91", "#CE93D8", "#90CAF9"]
LINE_COLORS = {"def": ACCENT, "out": HOT, "in": COOL, "clamp": ACCENT}

# Layout of the 8 x 14.2 frame, top to bottom: title bar and status chips, the panel (users, load balancer,
# the servers in a row with Bit on the newest, the caption), the CPU chart, the policy code. The bottom
# quarter (y < -3.55) stays clear for the app's buttons (only the code window's bottom padding dips into it);
# the watermark sits in the bottom-right corner.
HEADER_Y, ROW_Y = 5.15, 4.65
PANEL_TOP, PANEL_BOTTOM = 4.35, -0.4
USER_ROWS, USER_COLS, USER_STEP, USER_SIZE = (3.92, 3.52), 12, 0.58, 0.32
MAX_USERS = len(USER_ROWS) * USER_COLS
LB_AT = np.array([0, 2.65, 0])
CARD_W, CARD_H, CARD_Y = 1.68, 1.3, 0.95
SLOT_X = [-2.67, -0.89, 0.89, 2.67]
CAPTION_Y = -0.08
CHART_AT, CHART_SIZE = np.array([0, -1.1, 0]), (7.5, 1.1)
CODE_TOP, CODE_BOTTOM = -1.8, -3.9
HEADLINE_Y, BUTTON_Y = (-1.25, -2.0), -3.2

SCALE_OUT, SCALE_IN = 70, 30  # the policy, in % CPU
PEAK, NIGHT, CALM = 220, 20, 15  # load (in % of one server) at the spike, at night and on the first frame
PACKET_TIME = 1.1
PRICE = 0.10  # dollars per server-hour
SAMPLE, WINDOW = 1 / 15, 90  # the chart keeps 6 s of history


# ---------------------------------------------------------------- sound design
def _lowpass(x, hz, order=2):
    return signal.lfilter(*signal.butter(order, hz / (SR / 2)), x)


def _highpass(x, hz, order=2):
    return signal.lfilter(*signal.butter(order, hz / (SR / 2), btype="high"), x)


def _bandpass(x, lo, hi, order=2):
    return signal.lfilter(*signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band"), x)


def _put(buf, sig, at):
    """Mix `sig` into `buf` starting at `at` seconds."""
    s = int(at * SR)
    n = min(sig.size, buf.size - s)
    buf[s:s + n] += sig[:n]
    return buf


def _bell(hz, duration, decay=5.0):
    """A soft bell: inharmonic partials, the higher ones dying faster."""
    t = _t_axis(duration)
    partials = ((1, 1.0, 1.0), (2.0, 0.35, 1.6), (2.76, 0.22, 2.3), (5.4, 0.1, 3.5), (8.93, 0.04, 5.0))
    tone = sum(a * np.sin(2 * np.pi * hz * r * t) * np.exp(-t * decay * k) for r, a, k in partials)
    return tone * np.minimum(1, t / 0.002)


def _reverb(x, seconds=1.1, decay=4.5, mix=0.25, seed=5):
    """A small room: the dry sound plus a dark, decaying noise tail."""
    t = _t_axis(seconds)
    ir = _lowpass(np.random.default_rng(seed).normal(size=t.size), 4500) * np.exp(-t * decay)
    ir[:int(SR * 0.015)] = 0  # pre-delay
    dry = np.concatenate([x, np.zeros(t.size)])
    wet = signal.fftconvolve(dry, ir)[:dry.size]
    return dry + mix * wet / (np.max(np.abs(wet)) or 1) * np.max(np.abs(x))


def _relay(rng, n=220):
    """The click of a power relay."""
    return _highpass(rng.normal(size=n), 2000) * np.exp(-np.arange(n) / 30)


def make_scale_sfx():
    """Synthesize the server sounds into assets/sfx/, timed to the 120 BPM grid (a 16th is 0.125 s)."""
    rng = np.random.default_rng(23)
    sixteenth = BEAT / 4

    # Server boot: relay click, power hum and fans spinning up for one beat, then a rising two-note
    # chime on the next beat (when the server comes up) and the 16th after it.
    t = _t_axis(BEAT + 0.6)
    p = np.clip(t / (BEAT * 0.9), 0, 1)
    tail = np.where(t < BEAT, 1, np.exp(-(t - BEAT) * 7))
    hum_hz = 55 + 130 * (1 - (1 - p) ** 2)
    hum = (np.sin(2 * np.pi * np.cumsum(hum_hz) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(hum_hz) / SR)) * 0.5
    fan = _lowpass(rng.normal(size=t.size), 1800) * p ** 1.5 * (1 + 0.35 * np.sin(2 * np.pi * np.cumsum(4 + 46 * p) / SR))
    boot = (hum * np.minimum(1, t / 0.05) + fan * 0.35) * tail
    boot[:220] += _relay(rng) * 0.8
    _put(boot, _bell(1318.51, 0.4, 7) * 0.5, BEAT)
    _put(boot, _bell(1975.53, 0.47, 6) * 0.5, BEAT + sixteenth)
    _save("boot", _reverb(boot, mix=0.22), 0.6)

    # Shutdown: a falling two-note chime (on the beat and the 16th after), the hum winding down, the fans stopping.
    t = _t_axis(1.0)
    hz = 185 * np.exp(-t * 1.6) + 35
    hum = (np.sin(2 * np.pi * np.cumsum(hz) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(hz) / SR)) * np.exp(-t * 2.5) * 0.5
    fan = _lowpass(rng.normal(size=t.size), 1500) * np.exp(-t * 3.5) * 0.3
    fan *= 1 + 0.35 * np.sin(2 * np.pi * np.cumsum(3 + 40 * np.exp(-t * 2.5)) / SR)
    down = hum + fan
    down[:220] += _relay(rng) * 0.8
    _put(down, _bell(1975.53, 0.35, 7) * 0.35, 0.0)
    _put(down, _bell(1318.51, 0.5, 6) * 0.35, sixteenth)
    _save("shutdown", _reverb(down, mix=0.2), 0.55)

    # A policy line fires: a friendly two-tone notification, a 16th apart.
    alert = _put(_put(np.zeros(int(SR * 0.9)), _bell(880.0, 0.7, 4.5), 0), _bell(1318.51, 0.75, 4.5), sixteenth)
    _save("alert", _reverb(alert, mix=0.3), 0.5)

    # CPU at 100%: three eighth-note pulses of a gritty warning tone over a sub.
    t = _t_axis(3 * BEAT / 2)
    phase = t % (BEAT / 2)
    gate = np.where(phase < 0.18, np.minimum(1, phase / 0.005) * np.clip((0.18 - phase) / 0.01, 0, 1), 0) * np.exp(-phase * 3)
    tone = np.tanh(2.5 * np.sin(2 * np.pi * 466 * t)) + 0.6 * np.sin(2 * np.pi * 233 * t)
    _save("overload", _reverb(_lowpass(tone * gate, 4000) + np.sin(2 * np.pi * 58 * t) * gate * 0.5, mix=0.15), 0.55)

    # Traffic surge, two beats long: noise swelling from dark to bright, a rising sweep and a crowd of
    # tiny request blips, peaking on the beat it ends on.
    d = 2 * BEAT
    t = _t_axis(d)
    p = t / d
    swell = p ** 2 * np.clip((d - t) / 0.06, 0, 1)
    noise = rng.normal(size=t.size)
    surge = (_lowpass(noise, 500) * (1 - p) + _bandpass(noise, 900, 6000) * p * 0.6) * swell
    surge += np.sin(2 * np.pi * np.cumsum(90 + 700 * p ** 2) / SR) * swell * 0.25
    for at in np.sort(rng.uniform(0, 1, 50) ** 0.5) * (d - 0.06):  # denser towards the peak
        blip = np.sin(2 * np.pi * rng.uniform(500, 1600) * _t_axis(0.035)) * np.exp(-_t_axis(0.035) * 90)
        _put(surge, blip * 0.25 * (at / d), at)
    _save("surge", _reverb(surge, mix=0.2), 0.55)

    # 503: a digital glitch, bit-crushed square bursts at random pitches.
    parts = []
    for _ in range(14):
        n = int(SR * 0.025)
        square = np.sign(np.sin(2 * np.pi * rng.choice([95, 180, 360, 720, 1440]) * np.arange(n) / SR))
        parts.append(square * (rng.random() < 0.75))
    glitch = np.repeat(np.round(np.concatenate(parts) * 4)[::6] / 4, 6)
    _save("glitch", glitch * np.exp(-_t_axis(glitch.size / SR) * 5), 0.25)

    # Paying only for what you use: cash-register rattle, then a bright "ching" on the 16th.
    coin = np.zeros(int(SR * 1.3))
    for k in range(5):
        _put(coin, _bandpass(rng.normal(size=int(SR * 0.03)), 3000, 9000) * np.exp(-_t_axis(0.03) * 120), 0.02 * k)
    for hz, gain in ((2093.0, 1.0), (2637.0, 0.8), (3136.0, 0.5)):
        _put(coin, _bell(hz, 1.1, 3.2) * gain, sixteenth)
    _save("coin", _reverb(coin, mix=0.25), 0.55)

    # UI tap: a short tick with a soft body, for things popping in.
    t = _t_axis(0.1)
    tap = np.sin(2 * np.pi * 1650 * t) * np.exp(-t * 85)
    tap += 0.7 * np.sin(2 * np.pi * np.cumsum(260 * np.exp(-t * 30) + 120) / SR) * np.exp(-t * 45)
    tap[:30] += rng.normal(size=30) * np.exp(-np.arange(30) / 5) * 0.4
    _save("tap", tap, 0.4)


SCALE_SFX = ("boot", "shutdown", "alert", "overload", "surge", "glitch", "coin", "tap")


# ----------------------------------------------------------------- icons and text
_ICONS, _TEXTS = {}, {}


def icon(name, size, color=WHITE):
    """A Material Design icon from assets/icons/, `size` units on its longer side."""
    if name not in _ICONS:
        _ICONS[name] = SVGMobject(str(ICONS / f"{name}.svg")).set_stroke(width=0)
    glyph = _ICONS[name].copy()
    return glyph.scale(size / max(glyph.width, glyph.height)).set_fill(color, 1)


def tile(name, size, colors, angle=0.0):
    """An app-style icon tile: gradient rounded square, a soft top highlight, the white glyph and a shadow."""
    box = RoundedRectangle(width=size, height=size, corner_radius=size * 0.26, stroke_color=WHITE, stroke_width=1.5,
                           stroke_opacity=0.3)
    box.set_fill(colors, 1).set_sheen_direction(DOWN)
    shine = RoundedRectangle(width=size * 0.84, height=size * 0.38, corner_radius=size * 0.17, fill_color=WHITE,
                             fill_opacity=0.12, stroke_width=0).move_to(box.get_top() + DOWN * size * 0.25)
    glyph = icon(name, size * 0.56).rotate(angle).move_to(box)
    shadow = box.copy().set_fill(BLACK, 0.35).set_stroke(width=0).shift(DOWN * size * 0.06 + RIGHT * size * 0.03)
    return VGroup(shadow, box, shine, glyph)


def label(text, size, color, font=MONO):
    """Bold text, cached: the dashboard redraws its numbers every frame."""
    key = (text, size, str(color), font)
    if key not in _TEXTS:
        _TEXTS[key] = Text(text, font=font, weight=BOLD, font_size=size, color=color)
    return _TEXTS[key].copy()


def cpu_color(v):
    return OK_GREEN if v < 60 else WARN if v < 85 else HOT


def along(path, cum, t):
    """The point at fraction t of the polyline `path` (`cum`: cumulative length fractions)."""
    i = min(int(np.searchsorted(cum, t, side="right")) - 1, len(path) - 2)
    return path[i] + (path[i + 1] - path[i]) * (t - cum[i]) / (cum[i + 1] - cum[i])


class AutoScaling(BitScene):
    music = False  # the beat track under the video; True brings it back

    def setup(self):
        super().setup()
        self.rng = np.random.default_rng(21)
        self.servers, self.crowd, self.spawn = [], [], 0.0
        self.load = ValueTracker(CALM)  # demand, in % of one server

    # ---------------------------------------------------------------- beat grid
    def tick(self, *anims, beats=1, bit_free=True):
        """Play `anims` from this beat to the next one (or `beats` on), to the exact frame.

        manim rounds every play up to whole frames, so each play aims at its beat's absolute frame
        instead of adding run times. Bit bobs on the beat unless he is busy. The panel's top edge
        is the day going by: it fills up over the whole video.
        """
        if bit_free:
            anims += (self.bob(),)
        due = [anim for steps, anim in self.queued if steps == 0]
        self.queued = [(steps - 1, anim) for steps, anim in self.queued if steps]
        anims += tuple(due)
        self.b += beats
        self.set_progress(self.b % LENGTH / LENGTH)  # empty again on the last frame, as on the first
        fps = config.frame_rate
        frames = round(self.b * BEAT * fps) - round(self.time * fps)
        self.play(*(anims or (Wait(frozen_frame=False),)), run_time=frames / fps - 1e-4)
        assert round(self.time * fps) == round(self.b * BEAT * fps), "fell off the beat grid"

    def after(self, steps, anim):
        """Play `anim` with the tick `steps` ticks from now (0: the next one)."""
        self.queued.append((steps, anim))

    def sfx(self, name, offset=0.0, gain=None):
        """Sound effects start on the beat grid, not on the frame manim rounded the tick to."""
        super().sfx(name, offset + self.b * BEAT - self.time, (gain or 0) + MIX_TRIM)

    def lay_groove(self):
        """The track under the whole video, laid last once its sections are known, sixteenth by sixteenth.

        Intro (kick, offbeat hats); the 1x groove (clap, offbeat bass) through the spike; a build while the
        servers boot (kick and bass out, a snare roll, a riser); the drop as the load is shared, double time
        (sixteenth hats, rolling bass, pumping pads); night, half time (kick on 1 and 3, soft pads); then the
        1x groove with pads again for the takeaway and the subscribe.
        """
        def put(name, t, gain, trim=MIX_TRIM):
            self.add_sound(str(SFX / f"{name}.wav"), time_offset=t - self.time, gain=gain + trim)

        put("riser", (self.drop_at - 3) * BEAT, 4, trim=0)  # 1.5 s: it peaks on the drop
        put("cymbal", self.drop_at * BEAT, -3)
        put("cymbal", self.day_at * BEAT, -9)
        for q in range(round(self.b * 4)):
            b, pos = q / 4, q % 4  # the beat, and the sixteenth within it
            t, chord = b * BEAT, CHORDS[int(b // 2) % 4]
            intro = b < self.intro_end
            building = self.build_at <= b < self.drop_at
            double = self.drop_at <= b < self.night_at
            night = self.night_at <= b < self.day_at
            if double:
                put("ohat" if pos == 2 else "hat", t, -9 if pos == 2 else (-8 if pos == 0 else -13))
            elif pos == 2:
                put("hat", t, -10 if night else -8)
            if building:
                put("snare", t, -6 + 7 * (b - self.build_at) / (self.drop_at - self.build_at), trim=0)
                continue
            if pos == 0 and not (night and int(b) % 2):
                put("kick", t, -4 if night else -2)
            if intro:
                continue
            if pos == 0 and int(b) % 2 and not night:
                put("clap", t, -6)
            if pos == 2 or (double and pos):
                put(f"bass_{chord}", t, -6 if pos == 2 and not night else -10)
            if pos == 0 and int(b) % 2 == 0 and b >= self.drop_at:
                put(f"pad_{chord}", t, -9 if double else -14)

    def bob(self):
        """Bit squashes on the kick."""
        return self.bit.animate(rate_func=lambda t: there_and_back(min(1.0, t / 0.45))).stretch(0.9, 1, about_edge=DOWN)

    def caption(self, text, colors=None):
        """Replace the status line under the servers; returns the animations."""
        self.close_caption()
        new = Text(text, font=FONT, weight=BOLD, font_size=34, color=TEXT_LIGHT, t2c=colors)
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

    def live(self, mob, step):
        """Call step(dt) every frame for `mob` itself. Animations copy a mobject along with its updaters,
        and the copies (an animation's start and target) must not redraw themselves."""
        mob.add_updater(lambda m, dt: step(dt) if m is mob else None)

    def behind(self, mob):
        """Put `mob` just above the background: wires and packets run under the panels."""
        self.mobjects.insert(1, mob)

    # ---------------------------------------------------------------- pieces
    def watermark(self):
        # Like Quicksort, this Short keeps the top of the frame for its title bar: the mark goes bottom-right.
        return super().watermark().to_corner(DR, buff=0.35)

    def background(self):
        """Deep navy with a faint dot grid, like graph paper. Oversized so moves never show an edge."""
        sky = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, fill_color=BG, fill_opacity=1,
                        stroke_width=0)
        dots = VGroup(*[Dot([x, y, 0], radius=0.014, color=WHITE, fill_opacity=0.12)
                        for x in np.arange(-4.75, 4.8, 0.5) for y in np.arange(-7.75, 7.8, 0.5)])
        return Group(sky, flatten(dots))

    def chip(self, text, color=TEXT_LIGHT, dot=None, glyph=None):
        parts = VGroup(label(text, 22, color))
        if dot:
            parts.add_to_back(Dot(radius=0.07, color=dot))
        if glyph:
            parts.add_to_back(glyph)
        parts.arrange(RIGHT, buff=0.15)
        box = RoundedRectangle(width=parts.width + 0.45, height=0.52, corner_radius=0.08, fill_color=BG,
                               fill_opacity=1, stroke_color=color, stroke_width=2)
        return VGroup(box, parts.move_to(box))

    def replace(self, name, new):
        """Swap a status widget on the spot: it changes on the beat, with no fade."""
        self.remove(getattr(self, name))
        setattr(self, name, new)
        self.add(new)

    def set_servers(self):
        n = len(self.servers)
        self.replace("server_chip", self.chip(f"SERVERS {n}/4", ACCENT if n > 1 else TEXT_LIGHT)
                     .move_to([3.75, HEADER_Y, 0], aligned_edge=RIGHT))
        self.replace("cost_chip", self.chip(f"${n * PRICE:.2f}/h", TEXT_MUTED)
                     .next_to(self.users_chip, RIGHT, buff=0.15))

    def set_users(self, count, night=False):
        sky = icon("weather-night", 0.26, "#B3C7FF") if night else icon("white-balance-sunny", 0.26, ACCENT)
        self.replace("users_chip", self.chip(f"USERS {count}", glyph=sky).move_to([-3.75, ROW_Y, 0], aligned_edge=LEFT))
        if len(self.cost_chip):
            self.cost_chip.next_to(self.users_chip, RIGHT, buff=0.15)

    def set_phase(self, text, color):
        self.replace("phase_chip", self.chip(text, color, dot=color).move_to([3.75, ROW_Y, 0], aligned_edge=RIGHT))

    def set_progress(self, fraction):
        """The panel's top edge fills up, from noon round to the next noon."""
        w = 7.5 - 0.3
        bar = Line([-w / 2, PANEL_TOP, 0], [-w / 2 + w * max(fraction, 0.001), PANEL_TOP, 0], stroke_color=ACCENT,
                   stroke_width=6, stroke_opacity=1 if fraction else 0)
        self.replace("progress", bar)

    def goto(self, line):
        """Move the code highlight to LINE[line], in that line's colour."""
        return self.cbar.animate(rate_func=snap).set_y(self.code.code_lines[LINE[line]].get_y()).set_fill(
            LINE_COLORS[line], 0.25)

    def ring(self, mob, color=WHITE):
        """An outline bursting off `mob`: the visible hit of a beat."""
        ring = mob.copy().set_fill(opacity=0).set_stroke(color, 6, 1)
        return ring.animate(remover=True, rate_func=rate_functions.ease_out_cubic).scale(1.25).set_stroke(opacity=0)

    def user_spots(self):
        """Seats for the user icons, nearest the middle first."""
        spots = [np.array([(c - (USER_COLS - 1) / 2) * USER_STEP, y, 0]) for y in USER_ROWS for c in range(USER_COLS)]
        middle = np.array([0, sum(USER_ROWS) / 2, 0])
        return sorted(spots, key=lambda s: np.linalg.norm((s - middle) * [1, 1.6, 0]))

    def crowd_to(self, n):
        """Animate the crowd to n users; newcomers take the middle seats, leavers go from the edge."""
        spots, anims = self.user_spots(), []
        while len(self.crowd) < n:
            k = len(self.crowd)
            u = icon("account", USER_SIZE, USER_COLORS[k % len(USER_COLORS)]).move_to(spots[k])
            self.crowd.append(u)
            anims.append(FadeIn(u, scale=0.3))
        while len(self.crowd) > n:
            anims.append(FadeOut(self.crowd.pop(), scale=0.3))
        return LaggedStart(*anims, lag_ratio=0.15, rate_func=snap)

    def server_card(self, k):
        """A server: icon tile, name, big CPU % and a CPU bar. refresh() redraws it from card.shown and card.state."""
        body = RoundedRectangle(width=CARD_W, height=CARD_H, corner_radius=0.16, fill_color=CARD, fill_opacity=1,
                                stroke_color=CARD_EDGE, stroke_width=2.5).move_to([SLOT_X[k], CARD_Y, 0])
        badge = tile("server", 0.46, BLUE_T).move_to(body.get_corner(UL) + np.array([0.35, -0.35, 0]))
        name = label(f"web-{k + 1}", 18, TEXT_LIGHT).next_to(badge, RIGHT, buff=0.14)
        track = RoundedRectangle(width=CARD_W - 0.3, height=0.13, corner_radius=0.065, fill_color="#11142B",
                                 fill_opacity=1, stroke_width=0).move_to(body.get_bottom() + UP * 0.2)
        spinner = Arc(radius=0.33, angle=1.4 * PI, stroke_color=ACCENT, stroke_width=4).move_to(badge[1])
        fire = icon("fire", 0.36, "#FF7043").move_to(badge[1].get_corner(UR) + np.array([0.02, 0.04, 0]))
        card = VGroup(self.shadow(body), body, badge, name, track, VMobject(), VMobject(), spinner, fire)
        card.body, card.badge, card.name, card.track = body, badge, name, track
        card.fill, card.pct, card.spinner, card.fire = card[5], card[6], spinner, fire
        card.state, card.shown, card.look, card.last = "up", 0.0, None, None
        return card

    def refresh(self, card):
        v, track = card.shown, card.track
        booting = card.state == "boot"
        bar = RoundedRectangle(width=max(track.height, track.width * v / 100), height=track.height,
                               corner_radius=track.height / 2, stroke_width=0, fill_opacity=1,
                               fill_color=GRAY_B if booting else cpu_color(v))
        card.fill.become(bar.move_to(track.get_left(), aligned_edge=LEFT))
        text = "booting" if booting else f"{round(v)}%"
        if text != card.last:
            pct = label(text, 20, TEXT_MUTED) if booting else label(text, 32, cpu_color(round(v)))
            card.pct.become(pct.move_to(track.get_center() + UP * 0.36))
            card.last = text
        look = "boot" if booting else "hot" if v >= 95 else "up"
        if look != card.look:
            card.badge[1].set_fill({"boot": GRAY_T, "hot": RED_T, "up": BLUE_T}[look], 1)
            card.spinner.set_stroke(opacity=1 if booting else 0)
            card.fire.set_opacity(1 if look == "hot" else 0)
            card.look = look

    def up(self):
        return [c for c in self.servers if c.state == "up"]

    def tick_card(self, card, dt):
        """Per frame: the CPU eases towards its share of the load."""
        target = 0.0
        if card.state == "boot":
            card.spinner.rotate(-dt * 6)
        elif card.state == "up":
            target = min(100.0, self.load.get_value() / len(self.up()))
        card.shown += (target - card.shown) * min(1.0, dt * 4)
        self.refresh(card)

    def avg_cpu(self):
        up = self.up()
        return sum(c.shown for c in up) / len(up) if up else 0.0

    def wire(self, card):
        return Line(self.hub, card.body.get_top(), stroke_color=CARD_EDGE, stroke_width=3)

    def make_chart(self):
        w, h = CHART_SIZE
        panel = RoundedRectangle(width=w, height=h, corner_radius=0.15, fill_color="#161935", fill_opacity=0.92,
                                 stroke_color=CARD_EDGE, stroke_width=2).move_to(CHART_AT)
        chart = VGroup(self.shadow(panel), panel)
        head = VGroup(icon("cpu-64-bit", 0.26, TEXT_MUTED), label("AVG CPU", 18, TEXT_MUTED, FONT)).arrange(RIGHT, buff=0.1)
        chart.add(head.move_to(panel.get_corner(UL) + np.array([0.2, -0.22, 0]), aligned_edge=LEFT))
        x0, x1, y0, y1 = self.plot_box(chart)
        for level, color in ((SCALE_OUT, HOT), (SCALE_IN, COOL)):
            y = y0 + (y1 - y0) * level / 100
            chart.add(DashedLine([x0, y, 0], [x1, y, 0], dash_length=0.08, stroke_width=2, color=color, stroke_opacity=0.8),
                      label(f"{level}%", 14, color).move_to([x0 - 0.07, y, 0], aligned_edge=RIGHT))
        chart.area, chart.curve, chart.value = VMobject(), VMobject(), VMobject()
        chart.add(chart.area, chart.curve, chart.value)
        self.reset_chart(chart)
        return chart

    def reset_chart(self, chart):
        chart.history, chart.clock, chart.last = [float(CALM)] * WINDOW, 0.0, None
        self.draw_chart(chart)

    def plot_box(self, chart):
        panel = chart[1]
        return panel.get_left()[0] + 0.62, panel.get_right()[0] - 1.15, panel.get_bottom()[1] + 0.15, panel.get_top()[1] - 0.4

    def draw_chart(self, chart):
        x0, x1, y0, y1 = self.plot_box(chart)
        pts = [np.array([x0 + (x1 - x0) * i / (WINDOW - 1), y0 + (y1 - y0) * v / 100, 0]) for i, v in enumerate(chart.history)]
        v = chart.history[-1]
        chart.curve.set_points_as_corners(pts).set_stroke(cpu_color(v), 4)
        chart.area.set_points_as_corners(pts + [np.array([x1, y0, 0]), np.array([x0, y0, 0]), pts[0]])
        chart.area.set_fill(cpu_color(v), 0.15).set_stroke(width=0)
        if round(v) != chart.last:
            chart.value.become(label(f"{round(v)}%", 32, cpu_color(round(v)))
                               .move_to([(x1 + chart[1].get_right()[0]) / 2 + 0.05, chart[1].get_y() - 0.08, 0]))
            chart.last = round(v)

    def chart_step(self, chart, dt):
        chart.clock += dt
        while chart.clock >= SAMPLE:
            chart.clock -= SAMPLE
            chart.history = chart.history[1:] + [self.avg_cpu()]
        self.draw_chart(chart)

    def error_chip(self):
        box = RoundedRectangle(width=1.25, height=0.5, corner_radius=0.25, fill_color="#B00020", fill_opacity=1,
                               stroke_color=WHITE, stroke_width=2.5)
        text = VGroup(icon("alert-circle", 0.3), label("503", 24, WHITE)).arrange(RIGHT, buff=0.1).move_to(box)
        return VGroup(box, text)

    # ------------------------------------------------------------ traffic
    def flow_step(self, flow, dt):
        """Per frame: send new requests (more with more load) and move the ones in flight."""
        up = self.up()
        if self.crowd and up:
            self.spawn += dt * min(28.0, 2.0 + self.load.get_value() / 7)
        while self.spawn >= 1:
            self.spawn -= 1
            if self.crowd and up:
                self.send(flow, up[self.rng.integers(len(up))])
        for p in list(flow):
            p.t += dt / PACKET_TIME
            if p.t >= 1:
                flow.remove(p)
                continue
            pos = along(p.path, p.cum, p.t)
            if p.fail and p.t > 0.75:  # an overloaded server drops it
                k = (p.t - 0.75) / 0.25
                pos = pos + DOWN * 0.6 * k ** 2 + RIGHT * 0.3 * k
                p[0].set_fill(HOT, 0.25 * (1 - k))
                p[1].set_fill(HOT, 1 - k)
            p.move_to(pos)

    def send(self, flow, card):
        src = self.crowd[self.rng.integers(len(self.crowd))].get_center()
        path = [src, self.hub, card.body.get_top() + DOWN * 0.1]
        legs = np.array([np.linalg.norm(b - a) for a, b in zip(path, path[1:])])
        p = VGroup(Dot(radius=0.1, color=PACKET, fill_opacity=0.25), Dot(radius=0.045, color=PACKET)).move_to(src)
        p.path, p.cum, p.t = path, np.concatenate([[0], np.cumsum(legs)]) / legs.sum(), 0.0
        p.fail = card.shown >= 97 and self.rng.random() < 0.5
        flow.add(p)

    def hop_to(self, card):
        """Bit jumps onto the top of `card`."""
        target = self.bit.get_center() + card.body.get_top() - self.bit.get_bottom()
        self.sfx("pop", gain=-4)
        return self.bit.animate(path_arc=-PI / 2 if target[0] > self.bit.get_x() else PI / 2,
                                rate_func=lambda t: smooth(min(1.0, t / 0.7))).move_to(target)

    def boot(self, extra=()):
        """The next server appears greyed out with a spinner, plugged into the load balancer; up on the next beat."""
        card = self.server_card(len(self.servers))
        card.state = "boot"
        self.refresh(card)
        card.wire = self.wire(card)
        self.behind(card.wire)
        self.servers.append(card)
        self.set_servers()
        self.sfx("boot")
        self.tick(FadeIn(card, scale=0.8, rate_func=snap), Create(card.wire, rate_func=snap), *extra)
        self.live(card, lambda dt: self.tick_card(card, dt))
        return card

    def come_up(self, card, extra=()):
        """The booted server joins the load balancer; Bit hops onto it."""
        card.state = "up"
        self.tick(self.hop_to(card), self.ring(card.body, OK_GREEN), Flash(card.badge, color=OK_GREEN, flash_radius=0.45,
                                                                          rate_func=snap), *extra, bit_free=False)

    def shut_down(self, extra=()):
        """The newest server switches off; Bit hops back onto the one before it."""
        card = self.servers.pop()
        card.state = "off"
        card.clear_updaters()
        self.set_servers()
        self.sfx("shutdown", gain=-2)
        self.tick(FadeOut(card, shift=DOWN * 0.3, scale=0.8, rate_func=snap), FadeOut(card.wire, rate_func=snap),
                  self.hop_to(self.servers[-1]), *extra, bit_free=False)

    def fire(self, line, gain=-2):
        """A policy line fires: the highlight jumps to it with a notification; returns the animations."""
        self.sfx("alert", gain=gain)
        return [self.goto(line), Indicate(self.code.code_lines[LINE[line]], color=LINE_COLORS[line], scale_factor=1.06,
                                          rate_func=lambda t: there_and_back(min(1.0, t / 0.8)))]

    # ---------------------------------------------------------------- timeline
    def construct(self):
        if any(not (SFX / f"{name}.wav").exists() for name in SFX_NAMES):
            make_sfx()
        if any(not (SFX / f"{name}.wav").exists() for name in BEAT_SFX):
            make_beat_sfx()
        if any(not (SFX / f"{name}.wav").exists() for name in SCALE_SFX):
            make_scale_sfx()
        self.camera.background_color = BG
        self.stage()
        self.b, self.queued = 0, []
        self.cap, self.cap_since = VGroup(), None

        self.first_frame()
        self.chapter("steady", "One server")
        self.moment("hook")   # the dashboard, Bit on web-1 and the question are all up on the first frame
        self.moment("topic")  # AUTOSCALING is the title on the first frame
        self.tick()
        self.tick()
        self.intro_end = self.b
        self.chapter("spike", "Traffic spike")
        self.spike()
        self.chapter("scale_out", "CPU over 70%: add servers")
        self.scale_out()
        self.chapter("night", "CPU under 30%: remove them")
        self.scale_in()
        self.chapter("takeaway", "Scale out, scale in")
        self.takeaway()
        self.chapter("outro", "Subscribe")
        self.subscribe()
        self.rewind()
        assert self.b == LENGTH, f"{self.b} beats, the loop needs {LENGTH}"
        self.close_caption()
        if self.music:
            self.lay_groove()

    def first_frame(self):
        """Everything on screen at 0s: one calm server, three users, Bit, the chart, the policy (also the loop's last frame)."""
        panel = RoundedRectangle(width=7.5, height=PANEL_TOP - PANEL_BOTTOM, corner_radius=0.15, fill_color="#161935",
                                 fill_opacity=0.92, stroke_color=CARD_EDGE, stroke_width=2)
        panel.move_to([0, (PANEL_TOP + PANEL_BOTTOM) / 2, 0])
        self.lb = tile("call-split", 0.72, PURPLE_T, angle=PI).move_to(LB_AT)
        self.hub = self.lb[1].get_center()
        # Two short lines, narrow enough to stay clear of Bit standing on web-2 or web-3.
        lb_label = Text("load\nbalancer", font=FONT, font_size=13, color=TEXT_MUTED, line_spacing=0.6)
        lb_label.next_to(self.lb, DOWN, buff=0.05)

        self.chart = self.make_chart()
        self.code = self.make_code(CODE)
        if self.code.height > CODE_TOP - CODE_BOTTOM:
            self.code.scale_to_fit_height(CODE_TOP - CODE_BOTTOM)
        self.code.move_to([0, CODE_TOP, 0], aligned_edge=UP)
        tag = Text("autoscaler policy", font=MONO, font_size=17, color=TEXT_MUTED)
        tag.move_to(self.code.background.get_corner(UR) + np.array([-0.2, -0.22, 0]), aligned_edge=RIGHT)
        self.code_panel = VGroup(self.shadow(self.code.background), self.code, tag)
        self.cbar = self.line_bar(self.code, LINE["def"], color=LINE_COLORS["def"]).set_fill(opacity=0.25)

        title = Text("AUTOSCALING", font=FONT, weight=BOLD, font_size=44, color=HEADLINE)
        self.add(panel, self.lb, lb_label, title.move_to([-3.75, HEADER_Y, 0], aligned_edge=LEFT),
                 self.chart, self.code_panel, self.cbar)
        self.server_chip = self.users_chip = self.cost_chip = self.phase_chip = self.progress = VGroup()
        self.set_users("120")
        self.set_phase("STEADY", OK_GREEN)
        self.set_progress(0)

        card = self.server_card(0)
        card.shown = CALM
        self.refresh(card)
        card.wire = self.wire(card)
        self.servers.append(card)
        self.set_servers()
        self.flow = VGroup()
        for mob in (self.flow, card.wire):
            self.behind(mob)
        self.crowd_to(3)  # seated straight away, no animation
        self.add(card, *self.crowd)
        self.caption(*FIRST_LINE)
        self.add(self.cap)  # already up on the first frame, no fade in

        self.bit = Bit().scale(0.4)
        self.bit.brows.become(self.bit.make_brows("raised"))
        self.add(self.stand(self.bit, card.body.get_top()))

        # Requests are already in flight on the first frame, as they are on the last.
        for _ in range(round(PACKET_TIME * config.frame_rate)):
            self.flow_step(self.flow, 1 / config.frame_rate)
        self.live(card, lambda dt: self.tick_card(card, dt))
        self.live(self.chart, lambda dt: self.chart_step(self.chart, dt))
        self.live(self.flow, lambda dt: self.flow_step(self.flow, dt))

    def spike(self):
        """The crowd floods in, the one server hits 100% and requests fail."""
        self.sfx("surge")
        self.set_users("10,000")
        self.set_phase("OVERLOAD", HOT)
        self.tick(self.crowd_to(MAX_USERS), self.load.animate(rate_func=linear).set_value(PEAK),
                  *self.caption("Traffic SPIKE!", {"SPIKE!": HOT}), beats=2)
        web1 = self.servers[0]
        errors = [self.error_chip().rotate(a).move_to(p) for p, a in
                  (([-0.2, CARD_Y + 0.4, 0], 0.1), ([1.6, CARD_Y - 0.35, 0], -0.08), ([2.75, CARD_Y + 0.5, 0], 0.06))]
        self.sfx("overload")
        self.sfx("glitch", gain=-2)
        self.tick(FadeIn(errors[0], scale=1.6, rate_func=snap), Wiggle(web1.badge, scale_value=1.2),
                  *self.caption("100% CPU. Requests FAIL!", {"100% CPU.": HOT, "FAIL!": HOT}),
                  self.bit.express("open", "worried"))
        for e in errors[1:]:
            self.sfx("glitch", gain=-2)
            self.tick(FadeIn(e, scale=1.6, rate_func=snap), beats=0.5)
        self.drop = self.bit.sweat_drop()
        self.sfx("tap", gain=-6)
        self.tick(FadeIn(self.drop, shift=DOWN * 0.1, rate_func=snap), beats=2)
        self.errors = errors

    def scale_out(self):
        """cpu > 70 fires: three servers boot one after another, on every other beat; the build drops on the shared load."""
        self.set_phase("SCALING OUT", WARN)
        self.tick(*self.fire("out", gain=0), *[FadeOut(e, scale=0.6, rate_func=snap) for e in self.errors],
                  FadeOut(self.drop, rate_func=snap), self.bit.express("smile", "raised"),
                  *self.caption("CPU > 70%? Add a server!", {"CPU > 70%?": HOT}))
        for k in range(3):
            if k == 1:
                self.build_at = self.b  # the second and third servers boot over the build-up
            card = self.boot(self.fire("out", gain=-6) if k else ())
            extra = self.caption("Still busy? Add more!", {"Still busy?": WARN}) if k == 1 else ()
            self.come_up(card, extra)
        self.tick()  # the CPUs settle
        assert self.b == 16, "the drop lands on bar 5's downbeat"

        self.moment("payoff")
        self.drop_at = self.b
        self.set_phase("BALANCED", OK_GREEN)
        cards = VGroup(*self.servers)
        self.sfx("ding", gain=-4)
        self.tick(self.goto("def"), *self.caption("Load shared. Nobody waits!", {"Nobody waits!": OK_GREEN}),
                  self.confetti(cards, count=50), *[self.ring(c.body, OK_GREEN) for c in self.servers],
                  self.bit.arms_up(), self.bit.express("grin", "raised"), beats=2, bit_free=False)
        # Eighth notes up the scale, one server each: they bounce in turn, Bit rides the last one.
        for pair in range(2):
            anims = []
            for half in range(2):
                k = 2 * pair + half
                self.sfx(f"note_{k + 3}", offset=half * BEAT / 2, gain=-1)

                def rise(t, start=half / 2):
                    return there_and_back(min(1.0, max(0.0, (t - start) / 0.5)))

                card = self.servers[k]
                mob = Group(card, self.bit) if k == 3 else card
                anims.append(mob.animate(rate_func=rise).shift(UP * 0.25))
            self.sfx("tap", gain=-4)
            self.tick(*anims, *([self.bit.arms_rest(), self.bit.express("smile", "raised")] if pair else []),
                      bit_free=False)

    def scale_in(self):
        """Night: the users leave and cpu < 30 switches the servers off, one a beat, until it reaches the last one."""
        self.night_at = self.b
        self.set_users("80", night=True)
        self.set_phase("SCALING IN", COOL)
        self.sfx("whoosh", gain=-6)
        self.tick(self.crowd_to(3), self.load.animate(rate_func=snap).set_value(NIGHT),
                  *self.caption("Night: traffic drops.", {"Night:": COOL}), beats=2)
        self.shut_down([*self.fire("in"), *self.caption("CPU < 30%? Remove one.", {"CPU < 30%?": COOL})])
        self.shut_down(self.fire("in", gain=-6))
        self.shut_down(self.fire("in", gain=-6))

        # The gag: the last server is under 30% too. It starts to switch off... and max(1, ...) catches it.
        web1 = self.servers[0]
        shade = web1.body.copy().set_fill(BLACK, 0.6).set_stroke(width=0)
        self.sfx("oops", gain=-2)
        self.tick(*self.fire("in", gain=-4), FadeIn(shade, rate_func=snap), self.bit.express("open", "worried"),
                  self.bit.arms_up(), *self.caption("Remove the LAST one?!", {"LAST": HOT}), beats=2, bit_free=False)
        self.moment("gag")
        stamp = VGroup(RoundedRectangle(width=1.5, height=0.55, corner_radius=0.1, fill_color=ACCENT, fill_opacity=1,
                                        stroke_color=INK, stroke_width=3), label("MIN 1", 26, INK))
        stamp.rotate(-10 * DEGREES).move_to(web1.body)
        self.sfx("thud", gain=-1)
        self.sfx("ding", offset=BEAT / 4, gain=-6)
        self.set_phase("STEADY", OK_GREEN)
        self.tick(self.goto("clamp"), FadeOut(shade, rate_func=snap), FadeIn(stamp, scale=2.2, rate_func=snap),
                  self.bit.arms_rest(), self.bit.express("grin", "raised"),
                  *self.caption("Nope. MIN 1 stays on!", {"MIN 1": ACCENT}), beats=3, bit_free=False)
        self.stamp = stamp

    def takeaway(self):
        """You pay for what runs; then the rule in two lines, over where the chart and code were."""
        self.day_at = self.b
        self.sfx("coin", gain=-2)
        self.tick(FadeOut(self.stamp, rate_func=snap), self.ring(self.cost_chip[0], ACCENT),
                  self.bit.express("smile", "raised"), *self.caption("Pay only for what you use.", {"Pay only": ACCENT}),
                  beats=2)
        words = VGroup(*[
            Text(text, font=FONT, weight=BOLD, font_size=50, t2c={key: color}, color=TEXT_LIGHT).move_to([0, y, 0])
            for text, key, color, y in (("Busy? Scale OUT.", "Scale OUT.", HOT, HEADLINE_Y[0]),
                                        ("Quiet? Scale IN.", "Scale IN.", COOL, HEADLINE_Y[1]))
        ])
        self.headline = words
        self.log("text", "Busy? Scale OUT. Quiet? Scale IN.", (LENGTH - 1 - self.b) * BEAT, words=6)  # until the rewind
        self.sfx("pop", gain=-4)
        self.sfx("whoosh", gain=-6)
        self.tick(FadeOut(self.chart, shift=DOWN * 0.3, rate_func=snap), FadeOut(self.code_panel, shift=DOWN * 0.3, rate_func=snap),
                  FadeOut(self.cbar, rate_func=snap), FadeIn(words[0], scale=1.4, rate_func=snap))
        self.sfx("pop", gain=-4)
        self.sfx("boing", gain=-8)
        self.tick(FadeIn(words[1], scale=1.4, rate_func=snap))

    def subscribe(self):
        self.moment("cta")
        self.button = self.subscribe_button().scale(0.9).move_to([0, BUTTON_Y, 0])
        self.sfx("pop")
        self.tick(FadeIn(self.button, shift=UP * 0.4, rate_func=snap), *self.caption("Subscribe for more!"),
                  self.bit.look(DOWN))
        self.tick(self.pulse(self.button, times=1))
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
        # Back to the first frame's face, so the rewind only has to bring back the dashboard.
        self.tick(self.bit.arms_rest(), self.bit.express("smile", "raised"), beats=0.5, bit_free=False)

    def rewind(self):
        """The loop: noon again, the chart and policy come back and the status reads as on the first frame."""
        self.moment("loop")
        self.sfx("rewind")
        anims = [FadeOut(m, rate_func=snap) for m in (self.headline, self.button, self.done)]
        self.reset_chart(self.chart)
        self.cbar.set_y(self.code.code_lines[LINE["def"]].get_y()).set_fill(LINE_COLORS["def"], 0.25)
        anims += [FadeIn(m, rate_func=snap) for m in (self.chart, self.code_panel, self.cbar)]
        anims += self.caption(*FIRST_LINE)
        self.cap_since = None  # the replay carries this line on: it was logged once, from 0s
        self.load.set_value(CALM)
        self.servers[0].shown = CALM
        self.set_users("120")
        self.set_servers()
        self.set_phase("STEADY", OK_GREEN)
        # The video ends as the dashboard is back; the replay's two opening beats are the pause before the spike.
        self.tick(*anims, bit_free=False)


class Thumbnail(ThumbnailMixin, AutoScaling):
    def design(self):
        """Shorts/Reels cover: AUTOSCALING in big letters over servers stacking up 1, 2, 4, and a cheering Bit."""
        stairs = VGroup()
        for col, n in enumerate((1, 2, 4)):
            for r in range(n):
                stairs.add(tile("server", 1.05, BLUE_T).move_to([col * 1.3, r * 1.15, 0]))
        stairs.move_to([0.9, -1.6, 0])
        arrow = icon("trending-up", 1.8, OK_GREEN).next_to(stairs, UP, buff=0.1).shift(LEFT * 1.0)
        words = VGroup(headline_text("AUTO", 160, ACCENT), headline_text("SCALING", 130, TEXT_LIGHT),
                       headline_text("in 20 seconds", 64, HEADLINE)).arrange(DOWN, buff=0.1)
        words.scale_to_fit_width(7.0).move_to(UP * 4.3)
        bit = Bit().scale(1.1).move_to([-2.2, -1.3, 0])
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("raised"))
        bit.pose_arms(150, 150)
        self.add(stairs, arrow, words, bit)
