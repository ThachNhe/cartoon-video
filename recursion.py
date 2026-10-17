"""Recursion: a standalone cartoon about recursion and the base case.

Everything this video needs is in this file: the Bit character, speech bubbles,
the NeuTTS narrator and the synthesized sound effects.

Render:  .venv/bin/manim -qh --fps 30 recursion.py Recursion
Preview: .venv/bin/manim -ql recursion.py Recursion
Set BIT_VOICE=0 to render without narration.

Channel avatar (2048x2048 PNG; the round one has a transparent outside):
    .venv/bin/manim -s -r 2048,2048 recursion.py ChannelAvatar
    .venv/bin/manim -s -t -r 2048,2048 recursion.py ChannelAvatarRound
"""

import hashlib
import os
import re
import subprocess
import wave
from pathlib import Path

import manimpango
import numpy as np
from manim import *

ROOT = Path(__file__).parent
SFX = ROOT / "assets" / "sfx"
CACHE_DIR = ROOT / "assets" / "voice"
REF_DIR = ROOT / "assets" / "voice_ref"
FONT_DIR = ROOT / "assets" / "fonts"

BG = "#1B1E3C"
ACCENT = "#FFD54F"
HEADLINE = "#FF6B35"
TEXT_MUTED = "#9AA0C8"
TEXT_LIGHT = "#E8EAF6"
CONSOLE_GREEN = "#A6E3A1"
FRAME_COLORS = ["#80DEEA", "#A5D6A7", "#FFF59D", "#FFAB91", "#CE93D8"]
INK = "#1B1B2F"
MOUTH_FILL = "#7B1E2B"
FONT = "Poppins"
# The NL build has no programming ligatures, which manim needs (one glyph per character).
MONO = "JetBrains Mono NL"
for _font in FONT_DIR.glob("*.ttf"):
    manimpango.register_font(str(_font))


# ---------------------------------------------------------------- sound effects
SR = 44100


def _t_axis(duration):
    return np.linspace(0, duration, int(SR * duration), endpoint=False)


def _sweep(f0, f1, duration, wobble=0.0, wobble_hz=0.0):
    t = _t_axis(duration)
    freq = np.linspace(f0, f1, t.size)
    if wobble:
        freq = freq * (1 + wobble * np.sin(2 * np.pi * wobble_hz * t))
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def _env(signal, attack=0.005, decay_power=1.0):
    n = signal.size
    a = max(1, int(SR * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[a:] = np.linspace(1, 0, n - a) ** decay_power
    return signal * e


def _save(name, signal, volume=0.6):
    SFX.mkdir(parents=True, exist_ok=True)
    signal = signal / (np.max(np.abs(signal)) or 1) * volume
    data = (signal * 32767).astype(np.int16)
    with wave.open(str(SFX / f"{name}.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())


def make_sfx():
    """Synthesize the cartoon sound effects into assets/sfx/."""
    rng = np.random.default_rng(7)

    _save("pop", _env(_sweep(500, 1100, 0.09), decay_power=2), 0.5)
    _save("blip", _env(_sweep(1300, 1300, 0.05), decay_power=2), 0.25)
    _save("boing", _env(_sweep(180, 420, 0.55, wobble=0.35, wobble_hz=14), decay_power=1.5))
    _save("slide_down", _env(_sweep(1400, 250, 0.7), attack=0.02, decay_power=0.5), 0.45)

    t = _t_axis(0.5)
    noise = rng.normal(size=t.size)
    smooth = np.convolve(noise, np.ones(40) / 40, mode="same")
    _save("whoosh", smooth * np.sin(np.pi * t / t[-1]) ** 2, 0.5)

    t = _t_axis(1.6)
    alarm_freq = np.where((t * 4).astype(int) % 2 == 0, 880, 660)
    alarm = np.sign(np.sin(2 * np.pi * np.cumsum(alarm_freq) / SR)) * 0.6
    _save("alarm", _env(alarm, decay_power=0.3), 0.3)

    t = _t_axis(0.9)
    crash = rng.normal(size=t.size) * np.exp(-t * 6) + np.sin(2 * np.pi * 60 * t) * np.exp(-t * 8) * 2
    _save("crash", crash, 0.7)

    t = _t_axis(1.0)
    ding = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate([1320, 2640, 3960]))
    _save("ding", ding * np.exp(-t * 4), 0.45)

    t = _t_axis(0.35)
    _save("rimshot_tss", _env(rng.normal(size=t.size), decay_power=3), 0.35)
    _save("rimshot_ba", _env(_sweep(220, 160, 0.12) + rng.normal(size=int(SR * 0.12)) * 0.3, decay_power=2), 0.5)
    _save("rimshot_dum", _env(_sweep(160, 110, 0.15), decay_power=2), 0.6)

    # Keyboard click: a bright, very short tick.
    t = _t_axis(0.035)
    click = rng.normal(size=t.size) * np.exp(-t * 180) + np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 250) * 0.5
    _save("key", np.diff(click, prepend=0), 0.35)

    # Spellcheck "oops": two descending beeps.
    oops = np.concatenate([_env(_sweep(520, 500, 0.12), decay_power=1.5), _env(_sweep(390, 370, 0.18), decay_power=1.5)])
    _save("oops", oops, 0.35)


SFX_NAMES = ("pop", "blip", "boing", "slide_down", "whoosh", "alarm", "crash", "ding", "rimshot_tss",
             "rimshot_ba", "rimshot_dum", "key", "oops")


# ------------------------------------------------------------------- narration
SAMPLE_RATE = 24000
# Part of the cache key: changing it regenerates every clip.
POST_FX = (
    "silenceremove=start_periods=1:start_threshold=-45dB"
    ":stop_periods=-1:stop_duration=0.25:stop_silence=0.25:stop_threshold=-45dB,"
    "loudnorm=I=-16:TP=-1.5:LRA=11"
)
MIN_RATE, MAX_RATE = 1.5, 3.8  # plausible words per second
MAX_ATTEMPTS = 5


def _load_dotenv(path=ROOT / ".env"):
    """Export KEY=value lines (e.g. HF_TOKEN) without overriding the real environment."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

VOICE_ENABLED = os.environ.get("BIT_VOICE", "1") != "0"


class Narrator:
    """Speaks in the voice assets/voice_ref/<ref>.{pt,wav} with its .txt transcript.

    With a pre-encoded <ref>.pt the light ONNX decoder is used (~1 GB RAM). A
    voice that only has a .wav needs the full NeuCodec encoder (~4 GB RAM) once;
    the codes are then saved as <ref>.pt so later runs stay light.
    """

    def __init__(self, ref="dave", pitch=1.25, backbone="neuphonic/neutts-air", device=None, seed=7):
        self.ref = ref
        self.pitch = pitch
        self.backbone = backbone
        self.device = device
        self.seed = seed
        self._tts = None
        self._ref_codes = None

    def _load(self):
        import torch
        from neutts import NeuTTS

        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        codes_path = REF_DIR / f"{self.ref}.pt"
        light = codes_path.exists()
        self._tts = NeuTTS(
            backbone_repo=self.backbone, backbone_device=device,
            codec_repo="neuphonic/neucodec-onnx-decoder" if light else "neuphonic/neucodec",
            codec_device="cpu" if light else device, seed=self.seed,
        )
        if light:
            self._ref_codes = torch.load(codes_path)
        else:
            self._ref_codes = self._tts.encode_reference(str(REF_DIR / f"{self.ref}.wav"))
            torch.save(self._ref_codes, codes_path)
        self._ref_text = (REF_DIR / f"{self.ref}.txt").read_text().strip()

    def clip(self, text):
        """Return the path of a WAV file speaking `text`, generating it if needed."""
        key = hashlib.sha1(f"{self.backbone}|{self.ref}|{self.pitch}|{self.seed}|{POST_FX}|{text}".encode()).hexdigest()[:16]
        path = CACHE_DIR / f"{key}.wav"
        if path.exists():
            return path

        import soundfile as sf

        if self._tts is None:
            self._load()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        raw = CACHE_DIR / f"{key}.raw.wav"
        # Raise the pitch without changing the speed (a cheap "cartoon robot" voice),
        # then apply POST_FX: tighten the pauses TTS sometimes leaves and level the loudness.
        pitch_fx = f"asetrate={SAMPLE_RATE * self.pitch:.0f},aresample={SAMPLE_RATE},atempo={1 / self.pitch:.4f}"
        words = len(text.split())
        # TTS occasionally babbles or rushes a line; retry with the next seed when
        # the speaking rate is implausible (normal speech here is ~2-3 words/s).
        for attempt in range(MAX_ATTEMPTS):
            self._tts._seed = self.seed + attempt
            sf.write(raw, self._tts.infer(text, self._ref_codes, self._ref_text), SAMPLE_RATE)
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(raw),
                "-af", f"{pitch_fx},{POST_FX},aresample={SAMPLE_RATE}",
                str(path),
            ], check=True)
            rate = words / self.duration(path)
            # Short exclamations are naturally slow, so only check them for rushing.
            if rate <= MAX_RATE and (rate >= MIN_RATE or words < 5):
                break
            print(f"voice: {rate:.1f} words/s for {text!r}, retrying with another seed")
        raw.unlink()
        return path

    @staticmethod
    def duration(path):
        import soundfile as sf

        return sf.info(str(path)).duration


# ------------------------------------------------------------------ characters
class Bit(VGroup):
    """Robot mascot drawn in layers: ground shadow, arms, glossy gradient body, brows.

    Face and arm positions are relative to the body, so expressions and gestures
    keep working after the character is moved or scaled. Methods that change the
    pose return animations for the scene to play.
    """

    BODY_TOP, BODY_BOTTOM, LIMB = "#9BE1FF", "#36A9E1", "#2F8FC4"
    REST = 14  # relaxed arm angle, in degrees outward from hanging straight down

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ground = Ellipse(width=1.5, height=0.22, fill_color=BLACK, fill_opacity=0.3, stroke_width=0).move_to(DOWN * 1.13)
        feet = VGroup(*[
            RoundedRectangle(width=0.46, height=0.3, corner_radius=0.13, fill_color=self.LIMB, fill_opacity=1,
                             stroke_color=INK, stroke_width=4).move_to([x, -0.98, 0])
            for x in (-0.38, 0.38)
        ])
        self.arms = VGroup(*[self._make_arm(side) for side in (-1, 1)])
        self._arm_angles = [0.0, 0.0]
        antenna = Line(UP * 0.9, UP * 1.26, stroke_color=self.LIMB, stroke_width=6)
        glow = Circle(radius=0.24, fill_color=ACCENT, fill_opacity=0.3, stroke_width=0).move_to(UP * 1.38)
        self.bulb = Circle(radius=0.12, fill_color=ACCENT, fill_opacity=1, stroke_color=INK, stroke_width=4).move_to(UP * 1.38)
        self.body = RoundedRectangle(width=1.6, height=1.8, corner_radius=0.55, stroke_color=INK, stroke_width=5)
        self.body.set_fill([self.BODY_TOP, self.BODY_BOTTOM], opacity=1).set_sheen_direction(DOWN)
        gloss = VGroup(
            RoundedRectangle(width=0.13, height=0.44, corner_radius=0.065, fill_color=WHITE, fill_opacity=0.55, stroke_width=0)
            .move_to([-0.64, 0.3, 0]),
            Dot([-0.64, 0.64, 0], radius=0.055, color=WHITE, fill_opacity=0.55),
        )
        badge = Text("</>", font=MONO, weight=BOLD, font_size=22, color="#1D6FA3").move_to([0, -0.66, 0])
        self.eyes = VGroup(*[
            Ellipse(width=0.4, height=0.5, fill_color=WHITE, fill_opacity=1, stroke_color=INK, stroke_width=3)
            .move_to([x, 0.26, 0])
            for x in (-0.32, 0.32)
        ])
        # Each pupil carries a white glint so the eyes catch the light.
        self.pupils = VGroup(*[
            VGroup(Dot(radius=0.1, color=INK), Dot(UR * 0.04, radius=0.035, color=WHITE))
            .move_to(eye.get_center() + DOWN * 0.04)
            for eye in self.eyes
        ])
        cheeks = VGroup(*[
            Ellipse(width=0.26, height=0.14, fill_color="#FF8A80", fill_opacity=0.7, stroke_width=0)
            .move_to([x, -0.12, 0])
            for x in (-0.58, 0.58)
        ])
        self.add(ground, feet, self.arms, antenna, glow, self.bulb, self.body, gloss, badge, cheeks,
                 self.eyes, self.pupils)
        self.brows = self.make_brows("neutral")
        self.mouth = self.make_mouth("smile")
        self.add(self.brows, self.mouth)
        self._head_parts = [antenna, glow, self.bulb, self.body, gloss, cheeks, self.eyes, self.pupils]
        self.pose_arms(self.REST, self.REST)

    def head(self):
        """Just the head (no arms, feet or ground shadow), e.g. for the channel icon."""
        return VGroup(*self._head_parts, self.brows, self.mouth)

    @staticmethod
    def _make_arm(side):
        shoulder = np.array([side * 0.8, 0.02, 0])
        limb = RoundedRectangle(width=0.2, height=0.62, corner_radius=0.1, fill_color=Bit.LIMB, fill_opacity=1,
                                stroke_color=INK, stroke_width=4).move_to(shoulder + [side * 0.04, -0.27, 0])
        hand = Circle(radius=0.13, fill_color=WHITE, fill_opacity=1, stroke_color=INK, stroke_width=4)
        hand.move_to(shoulder + [side * 0.04, -0.6, 0])
        pivot = Dot(shoulder, radius=0.001, fill_opacity=0)  # tracks the shoulder through moves and scales
        return VGroup(limb, hand, pivot)

    @property
    def unit(self):
        return self.body.width / 1.6

    def face_point(self, x, y):
        return self.body.get_center() + self.unit * np.array([x, y, 0])

    # ------------------------------------------------------------------- arms
    def pose_arms(self, left, right):
        """Set both arm angles instantly (degrees outward from hanging)."""
        for i, angle in enumerate((left, right)):
            side = -1 if i == 0 else 1
            arm = self.arms[i]
            arm.rotate(side * (angle - self._arm_angles[i]) * DEGREES, about_point=arm[2].get_center())
            self._arm_angles[i] = angle
        return self

    def arm_to(self, i, angle, **kwargs):
        """Animate arm i (0 = left, 1 = right) to `angle` degrees outward from hanging."""
        side = -1 if i == 0 else 1
        delta = side * (angle - self._arm_angles[i]) * DEGREES
        self._arm_angles[i] = angle
        arm = self.arms[i]
        return Rotate(arm, delta, about_point=arm[2].get_center(), **kwargs)

    def arms_rest(self, **kwargs):
        return AnimationGroup(self.arm_to(0, self.REST, **kwargs), self.arm_to(1, self.REST, **kwargs))

    def arms_up(self, **kwargs):
        return AnimationGroup(self.arm_to(0, 155, **kwargs), self.arm_to(1, 155, **kwargs))

    def point(self, i, angle=75, **kwargs):
        return self.arm_to(i, angle, run_time=kwargs.pop("run_time", 0.3), **kwargs)

    def wave(self, i=1, times=2):
        steps = [self.arm_to(i, 150, run_time=0.2)]
        for _ in range(times):
            steps += [self.arm_to(i, 118, run_time=0.14), self.arm_to(i, 155, run_time=0.14)]
        steps.append(self.arm_to(i, self.REST, run_time=0.25))
        return Succession(*steps)

    # ------------------------------------------------------------------- face
    BROWS = {  # (inner end height, outer end height) in body units
        "neutral": ((0.62, 0.6), (0.62, 0.6)),
        "raised": ((0.75, 0.72), (0.75, 0.72)),
        "worried": ((0.71, 0.58), (0.71, 0.58)),
        "angry": ((0.56, 0.67), (0.56, 0.67)),
        "smug": ((0.6, 0.6), (0.73, 0.76)),
    }

    def make_brows(self, kind):
        brows = VGroup()
        for side, (inner, outer) in zip((-1, 1), self.BROWS[kind]):
            brows.add(Line(self.face_point(side * 0.17, inner), self.face_point(side * 0.47, outer),
                           stroke_color=INK, stroke_width=7, cap_style=CapStyleType.ROUND))
        return brows

    def make_mouth(self, kind):
        u = self.unit
        c = self.face_point(0, -0.32)
        if kind == "smile":
            m = Arc(radius=0.26 * u, start_angle=PI * 1.2, angle=PI * 0.6, stroke_color=INK, stroke_width=7)
        elif kind == "grin":
            m = Arc(radius=0.28 * u, start_angle=PI, angle=PI)
            m.add_line_to(m.get_start())
            m.set_fill(MOUTH_FILL, 1).set_stroke(INK, 6)
        elif kind == "open":
            m = Ellipse(width=0.3 * u, height=0.38 * u, fill_color=MOUTH_FILL, fill_opacity=1, stroke_color=INK, stroke_width=6)
        elif kind == "flat":
            m = Line(LEFT * 0.18 * u, RIGHT * 0.18 * u, stroke_color=INK, stroke_width=7)
        elif kind == "wavy":
            m = ParametricFunction(
                lambda t: np.array([t, 0.05 * np.sin(t * 40), 0]), t_range=[-0.26, 0.26],
                stroke_color=INK, stroke_width=6,
            ).scale(u)
        elif kind == "smug":
            m = ArcBetweenPoints(LEFT * 0.2, RIGHT * 0.2 + UP * 0.1, angle=PI / 2, stroke_color=INK, stroke_width=7)
            m.scale(u)
            c = c + RIGHT * 0.06 * u
        elif kind == "frown":
            m = Arc(radius=0.26 * u, start_angle=PI * 0.2, angle=PI * 0.6, stroke_color=INK, stroke_width=7)
        else:
            raise ValueError(f"unknown mouth: {kind}")
        return m.move_to(c)

    def set_mouth(self, kind, **kwargs):
        return Transform(self.mouth, self.make_mouth(kind), **kwargs)

    def set_brows(self, kind, **kwargs):
        return Transform(self.brows, self.make_brows(kind), **kwargs)

    def express(self, mouth=None, brows=None, **kwargs):
        """Change mouth and/or brows together."""
        anims = [self.set_mouth(mouth, **kwargs)] if mouth else []
        anims += [self.set_brows(brows, **kwargs)] if brows else []
        return AnimationGroup(*anims)

    def look(self, direction=ORIGIN, **kwargs):
        d = np.array(direction, dtype=float)
        if np.linalg.norm(d) > 0:
            d = d / np.linalg.norm(d)
        return AnimationGroup(*[
            pupil.animate(**kwargs).move_to(eye.get_center() + d * 0.09 * self.unit)
            for pupil, eye in zip(self.pupils, self.eyes)
        ])

    def blink(self):
        center = self.eyes.get_center()
        return AnimationGroup(*[
            m.animate(rate_func=there_and_back, run_time=0.22).stretch(0.08, 1, about_point=center)
            for m in [*self.eyes, *self.pupils]
        ])

    def talk(self, duration):
        n = max(1, int(duration / 0.2))
        return Succession(*[
            self.mouth.animate(rate_func=there_and_back, run_time=duration / n).stretch(1.9, 1)
            for _ in range(n)
        ])

    def x_eyes(self):
        s = 0.13 * self.unit
        crosses = VGroup(*[
            VGroup(Line(p.get_center() + UL * s, p.get_center() + DR * s),
                   Line(p.get_center() + UR * s, p.get_center() + DL * s)).set_stroke(INK, 7)
            for p in self.pupils
        ])
        return Transform(self.pupils, crosses)

    def sweat_drop(self):
        drop = VGroup(
            Triangle(fill_color="#81D4FA", fill_opacity=1, stroke_width=0).scale(0.09 * self.unit),
            Circle(radius=0.085 * self.unit, fill_color="#81D4FA", fill_opacity=1, stroke_width=0),
        )
        drop[1].next_to(drop[0], DOWN, buff=-0.07 * self.unit)
        return drop.move_to(self.face_point(0.78, 0.7))


# -------------------------------------------------------------------- branding
CHANNEL = "BitByBit"


def avatar_head():
    """Bit's head drawn for icon sizes: bold outline, big double-glint eyes, open smile."""
    outline = 9
    stem = Line([0, 0.8, 0], [0, 1.28, 0], stroke_color=Bit.LIMB, stroke_width=11, cap_style=CapStyleType.ROUND)
    glow = Circle(radius=0.34, fill_color=ACCENT, fill_opacity=0.35, stroke_width=0).move_to([0, 1.42, 0])
    bulb = Circle(radius=0.17, fill_color=ACCENT, fill_opacity=1, stroke_color=INK, stroke_width=outline - 3)
    bulb.move_to([0, 1.42, 0])
    ears = VGroup(*[
        RoundedRectangle(width=0.26, height=0.62, corner_radius=0.12, fill_color=Bit.LIMB, fill_opacity=1,
                         stroke_color=INK, stroke_width=outline - 2).move_to([side * 1.07, -0.02, 0])
        for side in (-1, 1)
    ])
    face = RoundedRectangle(width=2.1, height=1.8, corner_radius=0.72, stroke_color=INK, stroke_width=outline)
    face.set_fill([Bit.BODY_TOP, Bit.BODY_BOTTOM], opacity=1).set_sheen_direction(DOWN)
    gloss = VGroup(
        RoundedRectangle(width=0.16, height=0.5, corner_radius=0.08, fill_color=WHITE, fill_opacity=0.65,
                         stroke_width=0).rotate(-0.25).move_to([-0.78, 0.3, 0]),
        Dot([-0.66, 0.64, 0], radius=0.065, color=WHITE, fill_opacity=0.65),
    )
    eyes, pupils = VGroup(), VGroup()
    for side in (-1, 1):
        eye = Ellipse(width=0.52, height=0.64, fill_color=WHITE, fill_opacity=1, stroke_color=INK,
                      stroke_width=outline - 4).move_to([side * 0.4, 0.14, 0])
        pupil = VGroup(
            Circle(radius=0.165, fill_color=INK, fill_opacity=1, stroke_width=0),
            Dot(UR * 0.06, radius=0.06, color=WHITE),
            Dot(DL * 0.075, radius=0.028, color=WHITE),
        ).move_to(eye.get_center() + DOWN * 0.03 + LEFT * side * 0.02)
        eyes.add(eye)
        pupils.add(pupil)
    brows = VGroup(*[
        Arc(radius=0.22, start_angle=PI * 0.25, angle=PI * 0.5, stroke_color=INK, stroke_width=outline,
            cap_style=CapStyleType.ROUND).move_to([side * 0.4, 0.62, 0])
        for side in (-1, 1)
    ])
    cheeks = VGroup(*[
        Ellipse(width=0.3, height=0.17, fill_color="#FF8A9A", fill_opacity=0.8, stroke_width=0).move_to([side * 0.72, -0.22, 0])
        for side in (-1, 1)
    ])
    mouth = Arc(radius=0.3, start_angle=PI, angle=PI)
    mouth.add_line_to(mouth.get_start())
    mouth.set_fill(MOUTH_FILL, 1).set_stroke(INK, outline - 3).move_to([0, -0.38, 0])
    tongue = Ellipse(width=0.26, height=0.13, fill_color="#FF7A8A", fill_opacity=1, stroke_width=0)
    tongue.move_to(mouth.get_bottom() + UP * 0.1)
    head = VGroup(stem, glow, bulb, ears, face, gloss, cheeks, eyes, pupils, brows, mouth, tongue)
    # Soft drop shadow from the solid shapes only (a glow's shadow would look like a smudge).
    shadow = VGroup(ears, face, bulb).copy().set_fill(BLACK, 0.22).set_stroke(width=0).shift(DOWN * 0.12 + RIGHT * 0.06)
    return VGroup(shadow, head).rotate(-6 * DEGREES)


def sunburst(size=1024, round=False, inner="#FFB37A", outer="#FF5A1F", rays=18):
    """Orange radial gradient with soft rays, drawn per pixel so it never bands."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dx, dy = (xx - size / 2) / (size / 2), (yy - size / 2) / (size / 2)
    r = np.hypot(dx, dy)
    t = np.clip(r / 1.25, 0, 1)[..., None]
    img = color_to_rgb(inner) * (1 - t) ** 1.4 + color_to_rgb(outer) * (1 - (1 - t) ** 1.4)
    beam = (np.sin(np.arctan2(dy, dx) * rays) > 0).astype(np.float32)[..., None]
    img = img + beam * 0.045 * (0.4 + t)
    img = img + np.random.default_rng(1).normal(0, 0.004, img.shape)  # fine grain against banding
    alpha = np.clip((1 - r) * size / 2, 0, 1) if round else np.ones_like(r)  # anti-aliased circle edge
    rgba = np.concatenate([np.clip(img, 0, 1), alpha[..., None]], axis=-1)
    return ImageMobject((rgba * 255).astype(np.uint8))


def channel_icon(size=1024, round=True, height=8, head_height=5.4, head_y=-0.05):
    """The channel avatar: Bit's head on the orange sunburst, `height` units tall.

    `head_height` and `head_y` place the head on an 8-unit disc; a taller head
    leaves a thinner orange rim. Outlines are designed for an 8-unit avatar and
    scale with it; otherwise a small watermark would drown in ink and a large
    export would look thin.
    """
    backdrop = sunburst(size, round).set(height=height)
    head = avatar_head().set(height=head_height).move_to(UP * head_y)
    head.scale(height / 8, about_point=ORIGIN, scale_stroke=True)
    return Group(backdrop, head)


def flatten(mob, opacity=1.0, px_per_unit=270):
    """Rasterize `mob` on a transparent canvas, so it fades as one picture.

    Fading a mobject fades each layer on its own, letting outlines and the
    shapes underneath show through each other.
    """
    pad = 0.05
    w, h = mob.width + 2 * pad, mob.height + 2 * pad
    cam = Camera(frame_width=w, frame_height=h, pixel_width=int(w * px_per_unit), pixel_height=int(h * px_per_unit),
                 frame_center=mob.get_center(), background_opacity=0)
    cam.capture_mobject(mob)
    return ImageMobject(cam.get_image()).set(height=h).move_to(mob.get_center()).set_opacity(opacity)


def wordmark(name=CHANNEL, size=72, color=TEXT_LIGHT):
    """The name in Poppins, with Bit's glowing antenna bulb as the dot of each "i" in "Bit"."""
    spelled = name.replace("Bit", "B\u0131t")  # dotless i, so the bulb can be its dot
    word = Text(spelled, font=FONT, weight=BOLD, font_size=size, color=color)
    bulbs = VGroup()
    glyphs = [ch for ch in spelled if not ch.isspace()]
    for i, ch in enumerate(glyphs):
        if ch == "\u0131":
            k = size / 72
            halo = Circle(radius=0.16 * k, fill_color=ACCENT, fill_opacity=0.3, stroke_width=0)
            halo.next_to(word[i], UP, buff=0.05 * k)
            bulbs.add(halo, Circle(radius=0.085 * k, fill_color=ACCENT, fill_opacity=1, stroke_width=0).move_to(halo))
    return VGroup(word, bulbs)


class SpeechBubble(VGroup):
    """Rounded comic bubble; call point_tail_to() after positioning it."""

    def __init__(self, text, font_size=34, max_width=6.5, **kwargs):
        super().__init__(**kwargs)
        self.text = Text(text, font=FONT, font_size=font_size, color=INK, line_spacing=0.9)
        if self.text.width > max_width:
            self.text.scale_to_fit_width(max_width)
        self.box = RoundedRectangle(
            width=self.text.width + 0.6, height=self.text.height + 0.45, corner_radius=0.25,
            fill_color=WHITE, fill_opacity=1, stroke_color=INK, stroke_width=4,
        )
        self.text.move_to(self.box)
        self.add(self.box, self.text)

    def point_tail_to(self, tip):
        box = self.box
        left, right = box.get_left()[0], box.get_right()[0]
        bottom, top = box.get_bottom()[1], box.get_top()[1]
        if tip[1] < bottom:
            base = np.array([np.clip(tip[0], left + 0.45, right - 0.45), bottom, 0])
            along, inward = RIGHT, UP
        elif tip[0] < left:
            base = np.array([left, np.clip(tip[1], bottom + 0.3, top - 0.3), 0])
            along, inward = UP, RIGHT
        else:
            base = np.array([right, np.clip(tip[1], bottom + 0.3, top - 0.3), 0])
            along, inward = UP, LEFT
        a = base - along * 0.17 + inward * 0.05
        b = base + along * 0.17 + inward * 0.05
        fill = Polygon(a, b, tip, fill_color=WHITE, fill_opacity=1, stroke_width=0)
        edges = VMobject().set_points_as_corners([a, tip, b]).set_stroke(INK, 4)
        self.add(fill, edges)
        shadow = VGroup(box.copy(), fill.copy()).set_fill(BLACK, 0.3).set_stroke(width=0).shift(DR * 0.07)
        self.add_to_back(shadow)
        return self


# ----------------------------------------------------------------------- scene
COUNTDOWN = """def countdown(n):
    if n == 0:
        print("Liftoff!")
        return
    print(n)
    countdown(n - 1)"""

NO_BASE_CASE = """def countdown(n):
    print(n)
    countdown(n - 1)"""

STACK_X = 4.6
STACK_BASE_Y = -3.3
FRAME_STEP = 0.68


class Recursion(Scene):
    narrator = Narrator(ref="dave", pitch=1.25)

    # ------------------------------------------------------------------ helpers
    def sfx(self, name, offset=0.0, gain=None):
        self.add_sound(str(SFX / f"{name}.wav"), time_offset=offset, gain=gain)

    def adopt(self, parent, mob):
        """Move a freshly animated top-level mobject into a group."""
        self.remove(mob)
        parent.add(mob)

    def top_level(self):
        """Top-level mobjects, excluding the channel watermark (it never shakes or fades with a scene)."""
        mark = getattr(self, "mark", None)
        return [m for m in self.mobjects
                if m is not mark and not any(m is not o and m in o.get_family() for o in self.mobjects)]

    def watermark(self):
        # A bigger head than the avatar's, so only a thin orange rim shows at this size.
        icon = channel_icon(size=256, height=0.42, head_height=6.8, head_y=-0.14)
        mark = Group(icon, wordmark(size=19, color=WHITE)).arrange(RIGHT, buff=0.12)
        return flatten(mark, opacity=0.42).to_corner(UR, buff=0.21)

    def stage(self):
        """Empty the scene down to the background and the watermark."""
        self.clear()
        self.add(self.background())
        if not hasattr(self, "mark"):
            self.mark = self.watermark()
        self.add_foreground_mobject(self.mark)

    def shake(self, strength=0.15, times=6):
        everything = Group(*self.top_level())
        for i in range(times):
            d = (RIGHT if i % 2 == 0 else UP) * strength * (1 - i / times)
            self.play(everything.animate.shift(d), run_time=0.03, rate_func=linear)
            self.play(everything.animate.shift(-d), run_time=0.03, rate_func=linear)

    def voice(self, text):
        """Queue a spoken line at the current time; returns its length in seconds."""
        if not VOICE_ENABLED:
            return 0.0
        clip = self.narrator.clip(text)
        self.add_sound(str(clip))
        return self.narrator.duration(clip)

    def say(self, bit, text, direction=UR, hold=None, keep=False, font_size=34, shift=ORIGIN, speech=None,
            gesture=None):
        """Show a speech bubble while Bit talks.

        `speech` overrides what is read aloud (e.g. "n equals zero"); `gesture` is an
        animation (wave, point...) played while talking.
        """
        bubble = SpeechBubble(text, font_size=font_size)
        # Anchor on head and body only, so raised arms don't push the bubble around.
        bubble.next_to(VGroup(bit.body, bit.bulb), direction, buff=0.2).shift(shift)
        half_w, half_h = config.frame_width / 2 - 0.25, config.frame_height / 2 - 0.25
        bubble.shift(RIGHT * max(0, -half_w - bubble.get_left()[0]) + LEFT * max(0, bubble.get_right()[0] - half_w))
        bubble.shift(DOWN * max(0, bubble.get_top()[1] - half_h))
        side = np.sign(direction[0])
        tip = bit.face_point(0.55 * side, 0.95) if side else bit.face_point(0.35, 1.0)
        bubble.point_tail_to(tip)

        if speech is None:
            # Shouted CAPS are for the bubble; read them as normal words.
            speech = re.sub(r"\b[A-Z]{2,}\b", lambda m: m.group().lower(), " ".join(text.split()))
        self.sfx("blip", gain=-8)
        self.play(GrowFromPoint(bubble, tip), run_time=0.25)
        spoken = self.voice(speech)
        if hold is None:
            hold = spoken + 0.4 if spoken else 0.8 + 0.3 * len(text.split())
        talk_time = spoken or hold * 0.6
        self.play(bit.talk(talk_time), *([gesture] if gesture else []))
        self.wait(max(0.15, hold - talk_time))
        if keep:
            return bubble
        self.play(FadeOut(bubble, scale=0.9), run_time=0.2)
        return None

    def background(self):
        """Night sky: deep navy, soft planets in the corners, faint stars. Oversized so shakes never show an edge."""
        sky = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2,
                        fill_color=BG, fill_opacity=1, stroke_width=0)
        planets = VGroup(
            Circle(radius=3.2, fill_color="#232756", fill_opacity=1, stroke_width=0).move_to([-7.2, 4.2, 0]),
            Circle(radius=4.0, fill_color="#20244F", fill_opacity=1, stroke_width=0).move_to([7.6, -4.6, 0]),
        )
        rng = np.random.default_rng(4)
        stars = VGroup(*[
            Dot([rng.uniform(-7, 7), rng.uniform(-4, 4), 0], radius=rng.uniform(0.012, 0.03),
                color=WHITE, fill_opacity=rng.uniform(0.15, 0.4))
            for _ in range(70)
        ])
        return VGroup(sky, planets, stars)

    def shadow(self, mob):
        """Soft drop shadow to lift panels off the background."""
        return mob.copy().set_fill(BLACK, 0.35).set_stroke(width=0).shift(DR * 0.08)

    def make_code(self, source, width=6.2):
        def build(src):
            return Code(
                code_string=src, language="python", formatter_style="one-dark",
                background="window", paragraph_config={"font": MONO},
            )

        # Same scale for every listing, so edited code keeps its font size.
        return build(source).scale(width / build(COUNTDOWN).width)

    def line_bar(self, code, i, color=ACCENT):
        lines = code.code_lines
        h = abs(lines[0].get_y() - lines[1].get_y())
        bar = Rectangle(
            width=code.background.width - 0.2, height=h,
            fill_color=color, fill_opacity=0.2, stroke_width=0,
        )
        return bar.move_to([code.background.get_x(), lines[i].get_y(), 0])

    def bar_to(self, bar, code, i, run_time=0.3):
        self.play(bar.animate.set_y(code.code_lines[i].get_y()), run_time=run_time)

    def stack_frame(self, n, color):
        box = RoundedRectangle(
            width=3.2, height=0.6, corner_radius=0.12,
            fill_color=color, fill_opacity=0.95, stroke_color=WHITE, stroke_width=2,
        )
        label = Text(f"countdown({n})", font=MONO, font_size=28, color=INK).move_to(box)
        return VGroup(self.shadow(box), box, label)

    # ----------------------------------------------------------------- timeline
    def construct(self):
        if any(not (SFX / f"{name}.wav").exists() for name in SFX_NAMES):
            make_sfx()
        self.camera.background_color = BG
        self.stage()
        bit, title = self.intro()
        bit = self.meet_bit(bit, title)
        bit, code = self.happy_path(bit)
        self.stack_overflow(bit, code)
        self.punchline()
        self.outro()

    def laptop(self):
        """Laptop seen from behind its lid, so Bit can type at the camera."""
        lid = RoundedRectangle(width=2.3, height=1.15, corner_radius=0.12, fill_color="#3B4175", fill_opacity=1,
                               stroke_color=INK, stroke_width=5)
        glow = Circle(radius=0.24, fill_color=ACCENT, fill_opacity=0.22, stroke_width=0).move_to(lid)
        logo = Text("{ }", font=MONO, weight=BOLD, font_size=30, color=ACCENT).move_to(lid)
        base = RoundedRectangle(width=2.9, height=0.2, corner_radius=0.08, fill_color="#4A4F70", fill_opacity=1,
                                stroke_color=INK, stroke_width=4).next_to(lid, DOWN, buff=-0.02)
        shadow = Ellipse(width=3.0, height=0.2, fill_color=BLACK, fill_opacity=0.3, stroke_width=0).next_to(base, DOWN, buff=0)
        return VGroup(shadow, lid, glow, logo, base)

    def intro(self):
        """Bit types the title on a laptop, typos it, and fixes it."""
        final = Text("RECURSION", font=FONT, weight=BOLD, font_size=120, color=HEADLINE).move_to(UP * 2.0)
        typo = Text("RECURSOIN", font=FONT, weight=BOLD, font_size=120, color=HEADLINE)
        typo.align_to(final, LEFT).align_to(final, DOWN)
        bit = Bit().move_to(DOWN * 1.7)
        laptop = self.laptop()
        laptop.shift(UP * (-2.45 - laptop[1].get_top()[1]))  # lid hides Bit's belly, hands rest on its edge

        self.sfx("whoosh")
        self.play(FadeIn(bit, shift=UP * 1.5), FadeIn(laptop, shift=UP * 1.5), run_time=0.5,
                  rate_func=rate_functions.ease_out_back)
        self.play(bit.blink())

        cursor = Rectangle(width=0.07, height=final.height * 1.1, fill_color=TEXT_LIGHT, fill_opacity=1, stroke_width=0)
        blink = {"t": 0.0}

        def blink_cursor(m, dt):
            blink["t"] += dt
            m.set_opacity(1 if blink["t"] % 0.8 < 0.45 else 0)

        def cursor_after(letter):
            x = letter.get_right()[0] + 0.12 if letter is not None else final.get_left()[0]
            cursor.move_to([x, final.get_y(), 0])
            blink["t"] = 0.0  # stay solid while typing

        def keystroke(k, letter=None, remove=None, after=None, pause=0.0):
            hand = k % 2
            self.sfx("key", gain=-2 if k % 3 else 0)
            if remove is not None:
                self.remove(remove)
            cursor_after(after if after is not None else letter)
            tap = Succession(bit.arm_to(hand, 34, run_time=0.06), bit.arm_to(hand, Bit.REST, run_time=0.06))
            self.play(*([FadeIn(letter, scale=1.4)] if letter is not None else []), tap, run_time=0.12)
            if pause:
                self.wait(pause)

        cursor_after(None)
        cursor.add_updater(blink_cursor)
        self.add(cursor)
        self.play(bit.look(DOWN), run_time=0.2)
        self.wait(0.3)

        # R E C U R S O I N ... with a typist's uneven rhythm.
        pauses = [0.05, 0.02, 0.08, 0.02, 0.03, 0.12, 0.02, 0.03, 0.0]
        for k, letter in enumerate(typo):
            keystroke(k, letter, pause=pauses[k])

        # Spellcheck catches it; Bit freezes and looks at us.
        squiggle = ParametricFunction(
            lambda t: np.array([t, 0.07 * np.sin(t * 26), 0]), t_range=[0, VGroup(*typo[6:]).width],
            stroke_color=RED, stroke_width=6,
        ).next_to(VGroup(*typo[6:]), DOWN, buff=0.12)
        self.wait(0.25)
        self.sfx("oops")
        self.play(Create(squiggle), bit.look(UP), bit.express("flat", "raised"), run_time=0.35)
        self.wait(0.35)
        self.play(bit.look(ORIGIN), run_time=0.2)
        self.wait(0.6)

        # Backspace x3, then retype the right letters.
        self.play(bit.look(DOWN), bit.express("smile", "neutral"), FadeOut(squiggle), run_time=0.2)
        for k, letter in enumerate(reversed(typo[6:])):
            keystroke(k, remove=letter, after=typo[7 - k])  # N, I, O out; cursor steps back
        for k, letter in enumerate(final[6:]):
            keystroke(k + 1, letter, pause=0.03)

        # Fixed. Ding!
        title = VGroup(*typo[:6], *final[6:])
        for letter in title:
            self.remove(letter)
        self.add(title)
        cursor.clear_updaters()
        self.remove(cursor)
        self.sfx("ding")
        self.play(title.animate(rate_func=there_and_back).scale(1.06), bit.look(ORIGIN), bit.express("grin", "smug"),
                  run_time=0.35)
        spoken = self.voice("Recursion.")
        self.play(bit.talk(max(spoken, 0.5)))

        self.sfx("whoosh")
        self.play(FadeOut(laptop, shift=DOWN * 2), run_time=0.4, rate_func=rush_into)
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        return bit, title

    def meet_bit(self, bit, title):
        self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
        self.play(bit.set_mouth("grin"), run_time=0.2)
        self.say(bit, "Today we're learning\nRECURSION.", UR, gesture=bit.point(0, 165))
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.35), bit.set_mouth("smile"), run_time=0.4)
        self.say(bit, "Recursion is when a\nfunction calls ITSELF.", UR)
        self.play(bit.look(LEFT), run_time=0.2)
        self.play(bit.look(RIGHT), run_time=0.2)
        self.play(bit.look(ORIGIN), bit.express("smug", "smug"), run_time=0.2)
        self.say(bit, "Sounds scary?\nNah. Watch this.", UR)
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        return bit

    def happy_path(self, bit):
        code = self.make_code(COUNTDOWN).to_corner(UL, buff=0.5).shift(DOWN * 0.35)
        panel = RoundedRectangle(
            width=code.width, height=1.95, corner_radius=0.15,
            fill_color="#11111B", fill_opacity=1, stroke_color=GRAY_D, stroke_width=2,
        ).next_to(code, DOWN, buff=0.3, aligned_edge=LEFT)
        panel_label = Text("OUTPUT", font=MONO, font_size=20, color=GRAY_B).next_to(
            panel.get_corner(UL), DR, buff=0.15)
        stack_title = Text("CALL STACK", font=FONT, weight=BOLD, font_size=26, color=TEXT_MUTED).move_to(
            [STACK_X, STACK_BASE_Y - 0.35, 0])
        base = Line([STACK_X - 1.8, STACK_BASE_Y, 0], [STACK_X + 1.8, STACK_BASE_Y, 0], color=TEXT_MUTED, stroke_width=5)
        code_shadow, panel_shadow = self.shadow(code.background), self.shadow(panel)

        self.play(bit.animate.scale(0.7).move_to([1.4, -2.55, 0]), run_time=0.6)
        self.play(
            FadeIn(VGroup(code_shadow, code), shift=RIGHT * 0.5), FadeIn(panel_shadow), FadeIn(VGroup(panel, panel_label)),
            FadeIn(stack_title), Create(base), run_time=0.8,
        )

        output = VGroup()
        self.add(output)

        def print_line(text, color=CONSOLE_GREEN, run_time=0.2):
            line = Text(text, font=MONO, font_size=30, color=color)
            line.next_to(panel_label, DOWN, buff=0.12 + 0.36 * len(output), aligned_edge=LEFT)
            self.sfx("blip")
            self.play(FadeIn(line, shift=UP * 0.15), run_time=run_time)
            self.adopt(output, line)

        stack = VGroup()
        self.add(stack)

        def push(n, run_time):
            frame = self.stack_frame(n, FRAME_COLORS[len(stack) % len(FRAME_COLORS)])
            frame.move_to([STACK_X, STACK_BASE_Y + 0.36 + FRAME_STEP * len(stack), 0])
            self.sfx("pop")
            self.play(FadeIn(frame, shift=DOWN * 0.6), run_time=run_time)
            self.adopt(stack, frame)

        bar = self.line_bar(code, 0)
        self.play(FadeIn(bar), bit.look(UL), run_time=0.3)

        for n in (3, 2, 1, 0):
            slow = n == 3
            step = 0.35 if slow else 0.2
            self.bar_to(bar, code, 0, run_time=step)
            push(n, run_time=0.35 if slow else 0.25)
            if slow:
                self.play(bit.look(RIGHT), run_time=0.15)
                self.say(bit, "Every call gets its own\nbox on the call stack.", UP, shift=RIGHT * 0.4,
                         gesture=bit.point(1, 75))
                self.play(bit.look(UL), bit.arms_rest(run_time=0.25), run_time=0.25)
            self.bar_to(bar, code, 1, run_time=step)
            if slow:
                self.say(bit, "Is n == 0? Nope, it's 3.\nKeep going!", UP, shift=RIGHT * 0.4,
                         speech="Is n equal to zero? Nope, it's three. Keep going!")
            if n > 0:
                self.bar_to(bar, code, 4, run_time=step)
                print_line(str(n))
                self.bar_to(bar, code, 5, run_time=step)
                if slow:
                    self.say(bit, "...and now it calls\nITSELF with n - 1.", UP, shift=RIGHT * 0.4,
                             speech="And now, it calls itself, with n minus one.")
            else:
                self.bar_to(bar, code, 2, run_time=step)
                self.play(bit.express("grin", "raised"), bit.arms_up(run_time=0.3), run_time=0.3)
                print_line("Liftoff!", color=ACCENT, run_time=0.3)
                self.sfx("ding")
                self.play(Flash(output[-1], color=ACCENT, flash_radius=0.6), run_time=0.4)
                self.bar_to(bar, code, 3, run_time=step)

        self.play(bit.look(RIGHT), run_time=0.15)
        for frame in reversed(list(stack)):
            # Detach first: removing a submobject from the scene would split up `stack`.
            stack.remove(frame)
            self.add(frame)
            self.sfx("pop")
            self.play(FadeOut(frame, shift=UP * 0.6), run_time=0.22)
        self.play(FadeOut(bar), bit.look(ORIGIN), bit.express("smile", "neutral"), bit.arms_rest(run_time=0.25),
                  run_time=0.25)

        self.play(Indicate(code.code_lines[1], color=ACCENT, scale_factor=1.08), run_time=0.6)
        self.say(bit, "That  if n == 0  line is the\nBASE CASE. It's the exit door.", UP, shift=RIGHT * 0.4,
                 speech="That, if n equals zero, line is the base case. It's the exit door.",
                 gesture=bit.point(0, 125))
        self.play(bit.express("smug", "smug"), bit.arms_rest(run_time=0.25), run_time=0.25)
        self.say(bit, "Now... what if we\nDELETE the exit door?", UP, shift=RIGHT * 0.4)

        # Strike out the base case and throw it off screen.
        lines = code.code_lines
        strikes = VGroup(*[
            Line(lines[i].get_left() + LEFT * 0.05, lines[i].get_right() + RIGHT * 0.05, color=RED, stroke_width=6)
            for i in (1, 2, 3)
        ])
        self.play(LaggedStart(*[Create(s) for s in strikes], lag_ratio=0.35), run_time=0.6)
        flying = VGroup(lines[1].copy(), lines[2].copy(), lines[3].copy(), strikes)
        self.remove(strikes)
        self.add(flying)
        for i in (1, 2, 3):
            lines[i].set_opacity(0)
            code.line_numbers[i + 2].set_opacity(0)
        self.sfx("whoosh")
        self.play(flying.animate.shift(LEFT * 9).rotate(-0.6), run_time=0.45, rate_func=rush_into)
        self.remove(flying)

        new_code = self.make_code(NO_BASE_CASE)
        new_code.align_to(code, UL)
        self.play(
            Transform(code.background, new_code.background),
            Transform(code_shadow, self.shadow(new_code.background)),
            Transform(lines[0], new_code.code_lines[0]),
            Transform(lines[4], new_code.code_lines[1]),
            Transform(lines[5], new_code.code_lines[2]),
            *[Transform(code.line_numbers[i], new_code.line_numbers[i]) for i in range(3)],
            FadeOut(output),
            run_time=0.5,
        )
        self.remove(code)
        self.add(new_code)
        self.output, self.panel_label, self.stack, self.base = output, panel_label, stack, base
        return bit, new_code

    def stack_overflow(self, bit, code):
        stack, base, panel_label = self.stack, self.base, self.panel_label
        self.adopt(stack, base)
        frames = []
        output = VGroup()
        self.add(output)
        depth = ValueTracker(0)
        depth_label = always_redraw(lambda: Text(
            f"depth: {int(depth.get_value())}", font=MONO, font_size=30,
            color=interpolate_color(ManimColor(TEXT_LIGHT), ManimColor(RED), min(1, depth.get_value() / 600)),
        ).move_to([1.4, 3.35, 0]))
        self.play(FadeIn(depth_label), bit.express("smile", "neutral"), bit.look(UL), run_time=0.3)

        bar = self.line_bar(code, 0)
        self.add(bar)
        next_y = STACK_BASE_Y + 0.36

        for k, n in enumerate(range(3, -36, -1)):
            run_time = max(0.06, 0.4 * 0.8 ** k)
            frame = self.stack_frame(n, FRAME_COLORS[k % len(FRAME_COLORS)])
            anims = [bar.animate.set_y(code.code_lines[k % 3].get_y())]
            if next_y > 2.9:
                anims.append(stack.animate.shift(DOWN * FRAME_STEP))
                frame.move_to([STACK_X, next_y - FRAME_STEP, 0])
            else:
                frame.move_to([STACK_X, next_y, 0])
                next_y += FRAME_STEP

            line = Text(str(n), font=MONO, font_size=30, color=CONSOLE_GREEN)
            if len(output) >= 4:
                old = output[0]
                output.remove(old)
                anims += [output.animate.shift(UP * 0.36), FadeOut(old, shift=UP * 0.36)]
                line.next_to(panel_label, DOWN, buff=0.12 + 0.36 * 3, aligned_edge=LEFT)
            else:
                line.next_to(panel_label, DOWN, buff=0.12 + 0.36 * len(output), aligned_edge=LEFT)

            if k % 2 == 0 or run_time > 0.15:
                self.sfx("pop", gain=-6 if run_time < 0.15 else None)
            self.play(FadeIn(frame, shift=DOWN * 0.4), FadeIn(line), depth.animate.set_value(k + 1),
                      *anims, run_time=run_time)
            self.adopt(stack, frame)
            self.adopt(output, line)
            frames.append(frame)
            for f in frames:
                if f.get_top()[1] < -4.3 and f in stack:
                    stack.remove(f)

            if n == 0:
                self.say(bit, "Okay, n is 0, so we... wait.", UP, shift=RIGHT * 0.4,
                         speech="Okay, n is zero, so we... wait.")
                self.play(bit.express("flat", "raised"), run_time=0.15)
            elif n == -2:
                self.play(bit.express("open", "worried"), bit.look(UR), bit.arms_up(run_time=0.2), run_time=0.2)
                self.say(bit, "NEGATIVE TWO?!", UP, shift=RIGHT * 0.4, font_size=40, speech="Negative two?!")
                self.play(bit.set_mouth("wavy"), run_time=0.15)
                drop = bit.sweat_drop()
                self.play(FadeIn(drop, shift=DOWN * 0.1), run_time=0.15)
                bit.add(drop)
                self.remove(drop)

        # Panic ramp to the recursion limit.
        self.sfx("alarm")
        alarm_glow = Rectangle(
            width=config.frame_width, height=config.frame_height, stroke_width=0, fill_color=RED, fill_opacity=0
        )
        self.add(alarm_glow)
        for i in range(24):
            frame = self.stack_frame(-36 - i, RED_C).move_to([STACK_X, next_y - FRAME_STEP, 0])
            self.add(frame)
            tremble = RIGHT * 0.06 * (1 if i % 2 == 0 else -1)
            self.play(
                stack.animate.shift(DOWN * FRAME_STEP),
                depth.animate.set_value(39 + (1000 - 39) * ((i + 1) / 24) ** 2),
                bit.animate.shift(tremble),
                alarm_glow.animate.set_fill(opacity=0.18 if i % 4 < 2 else 0.04),
                run_time=0.065, rate_func=linear,
            )
            self.adopt(stack, frame)
            for f in list(stack):
                if f is not base and f.get_top()[1] < -4.3:
                    stack.remove(f)

        # Crash.
        box = RoundedRectangle(
            width=11.2, height=2.3, corner_radius=0.2,
            fill_color="#B00020", fill_opacity=0.97, stroke_color=WHITE, stroke_width=5,
        )
        err = VGroup(
            Text("RecursionError:", font=MONO, weight=BOLD, font_size=52, color=WHITE),
            Text("maximum recursion depth exceeded", font=MONO, font_size=38, color=WHITE),
        ).arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to(box)
        banner = VGroup(box, err).rotate(-3 * DEGREES).move_to(UP * 0.6)
        self.sfx("crash")
        self.play(FadeIn(banner, scale=2.5), alarm_glow.animate.set_fill(opacity=0.25), run_time=0.15, rate_func=rush_into)
        self.shake(strength=0.2, times=7)
        self.play(bit.x_eyes(), bit.set_mouth("open"), run_time=0.15)
        self.sfx("slide_down")
        self.play(Rotate(bit, -PI / 2, about_point=bit.get_corner(DR)), run_time=0.6, rate_func=rate_functions.ease_in_cubic)
        self.sfx("boing")
        self.shake(strength=0.08, times=3)
        self.wait(1.2)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.6)
        self.stage()

    def punchline(self):
        bit = Bit().move_to([-4.6, -0.6, 0])
        bandage = VGroup(*[
            RoundedRectangle(width=0.5, height=0.16, corner_radius=0.06, fill_color="#F5D6A8",
                             fill_opacity=1, stroke_color="#C9A27A", stroke_width=2).rotate(a)
            for a in (PI / 4, -PI / 4)
        ]).move_to(bit.face_point(0.6, 0.9))
        bit.add(bandage)
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.5)
        self.play(bit.blink())
        self.play(bit.express("flat", "worried"), run_time=0.15)
        self.say(bit, "Lesson learned:\nALWAYS write a base case.", UR)
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        self.say(bit, "Here's a little joke,\nso you never forget.", UR)
        bubble = self.say(bit, "To understand recursion,\nyou must first understand\nrecursion.",
                          UR, keep=True)
        self.play(bit.express("grin", "raised"), run_time=0.15)
        self.sfx("rimshot_ba")
        self.sfx("rimshot_dum", offset=0.18)
        self.sfx("rimshot_tss", offset=0.4)
        self.wait(1.0)

        # The joke recurses: zoom into an endless tunnel of itself.
        border = Rectangle(width=config.frame_width - 0.3, height=config.frame_height - 0.3,
                           stroke_color=TEXT_LIGHT, stroke_width=6)
        self.play(Create(border), run_time=0.4)
        world = VGroup(border, bit, bubble)
        pivot = np.array([4.6, -2.3, 0])
        ratio = 0.45
        copies = []
        for i in range(1, 6):
            copy = world.copy().scale(ratio ** i, about_point=pivot)
            self.sfx("pop", gain=-2 * i)
            self.play(FadeIn(copy, scale=0.6), run_time=0.22)
            copies.append(copy)
        self.wait(0.4)

        tunnel = Group(world, *copies)
        self.sfx("whoosh")
        for _ in range(3):
            deeper = world.copy().scale(ratio ** (len(copies) + 1), about_point=pivot)
            copies.append(deeper)
            tunnel.add(deeper)
            self.add(deeper)
            self.play(tunnel.animate.scale(1 / ratio, about_point=pivot), run_time=0.9, rate_func=linear)
        self.play(FadeOut(tunnel), run_time=0.4)
        self.stage()

    def outro(self):
        headline = Text("Always write your base case.", font=FONT, weight=BOLD, font_size=56, color=HEADLINE).to_edge(UP, buff=0.9)
        bit = Bit().move_to([-3.6, -1.0, 0])
        button = VGroup(RoundedRectangle(width=4.0, height=1.1, corner_radius=0.2, fill_color="#E53935",
                                         fill_opacity=1, stroke_width=0))
        button.add(Text("SUBSCRIBE", font=FONT, weight=BOLD, font_size=40).move_to(button[0]))
        button.move_to([2.8, -1.0, 0])

        self.play(Write(headline), FadeIn(bit, shift=UP * 0.5), run_time=1.0)
        self.play(FadeIn(button, scale=0.8), run_time=0.4)
        self.say(bit, "Base case reached.\nThe video can end now.", UR)

        cursor = Polygon([0, 0, 0], [0.0, -0.75, 0], [0.2, -0.56, 0], [0.42, -0.95, 0], [0.55, -0.88, 0],
                         [0.34, -0.5, 0], [0.6, -0.48, 0], fill_color=WHITE, fill_opacity=1,
                         stroke_color=INK, stroke_width=3).move_to([6.2, -3.4, 0])
        self.play(FadeIn(cursor), bit.look(RIGHT), run_time=0.3)
        self.play(cursor.animate.move_to(button.get_center() + DR * 0.3), run_time=0.7)
        self.sfx("pop")
        self.play(button.animate(rate_func=there_and_back).scale(0.9), run_time=0.2)
        done = VGroup(RoundedRectangle(width=4.0, height=1.1, corner_radius=0.2, fill_color=GRAY_D,
                                       fill_opacity=1, stroke_width=0))
        done.add(Text("SUBSCRIBED", font=FONT, weight=BOLD, font_size=40, color=GRAY_B).move_to(done[0]))
        done.move_to(button)
        self.sfx("ding")
        self.play(Transform(button, done), bit.set_mouth("grin"), bit.look(ORIGIN), run_time=0.3)
        self.play(bit.animate(rate_func=there_and_back).shift(UP * 0.4), run_time=0.35)
        self.play(bit.wave(i=0))
        self.play(bit.blink())
        self.wait(0.8)
        self.play(*[FadeOut(m) for m in [*self.top_level(), self.mark]], run_time=0.8)


class ChannelAvatar(Scene):
    """Square avatar for YouTube / Facebook (they crop it to a circle)."""

    round = False

    def construct(self):
        # With a square -r, manim keeps the 14.2-unit frame width and stretches the height to match.
        side = max(config.frame_width, config.frame_height)
        self.add(channel_icon(size=config.pixel_height, round=self.round, height=side))


class ChannelAvatarRound(ChannelAvatar):
    """Circular avatar with a transparent outside; render with -t."""

    round = True
