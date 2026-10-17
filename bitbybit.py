"""BitByBit: everything the channel's videos share.

The Bit character, speech bubbles, branding (watermark, avatar, wordmark), the NeuTTS
narrator, synthesized sound effects, audio mastering, the 16:9 / 9:16 format switch and
BitScene, the base scene with the helpers every video uses (say, stage, timeline logging,
the subscribe ending...). Each video is a file that imports this and defines its scenes.
"""

import hashlib
import json
import os
import re
import subprocess
import wave
from pathlib import Path

import manimpango
import numpy as np
from manim import *

# Manim's animation cache breaks the soundtrack: sounds queued right after a cached animation are
# dropped, and each cached one advances the clock by its nominal run_time instead of its rendered
# frames, so the audio drifts ahead of the picture.
config.disable_caching = True

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

# YouTube and Facebook play everything at about -14 LUFS and never turn a quiet video up.
TARGET_LUFS, TARGET_PEAK = -14.0, -1.5


def master_audio(movie):
    """Two-pass loudnorm of the finished movie's soundtrack to TARGET_LUFS; the picture is copied as is."""
    spec = f"loudnorm=I={TARGET_LUFS}:TP={TARGET_PEAK}:LRA=11"
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(movie), "-vn", "-af", f"{spec}:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    m = json.loads(log[log.rindex("{"):])
    measured = (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    mastered = movie.with_name(movie.stem + ".master" + movie.suffix)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(movie), "-c:v", "copy", "-af", spec + measured,
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(mastered)], check=True)
    mastered.replace(movie)


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

VERTICAL = os.environ.get("BIT_FORMAT") == "vertical"
if VERTICAL:
    # Portrait frame with the same pixels per unit as 16:9, so every mobject keeps its size.
    if config.pixel_width > config.pixel_height:
        config.pixel_width, config.pixel_height = config.pixel_height, config.pixel_width
    config.frame_width, config.frame_height = 8.0, 8.0 * 16 / 9


def pick(wide, tall):
    """The value for the current format: 16:9 or vertical 9:16."""
    return tall if VERTICAL else wide


# Shorts/Reels viewers swipe within seconds: open on the crash and skip the slower beats.
SHORT = VERTICAL


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


class BitScene(Scene):
    """Base scene: timeline logging, audio mastering, watermark, speech bubbles and the shared ending."""

    narrator = Narrator(ref="dave", pitch=1.25)
    code_width = pick(6.2, 7.2)  # make_code() width
    code_reference = None        # listing whose width sets the code scale (default: the listing itself)

    def render(self, preview=False):
        self.events = []
        rerun = super().render(preview)
        movie = Path(self.renderer.file_writer.movie_file_path)
        if not rerun and movie.exists():
            master_audio(movie)
            # The engagement checks in qc.py read this.
            timeline = {"duration": round(self.renderer.time, 2), "events": self.events}
            movie.with_suffix(".timeline.json").write_text(json.dumps(timeline, indent=1))
        return rerun

    # ------------------------------------------------------------------ helpers
    def log(self, kind, label, duration=0.0, **extra):
        """Record a timeline event: speech, text, sfx, chapter or moment (hook, payoff, joke, cta...)."""
        self.events.append({"t": round(self.renderer.time, 2), "kind": kind, "label": label,
                            "duration": round(duration, 2), **extra})

    def moment(self, name):
        self.log("moment", name)

    def chapter(self, name, title):
        """Start a section; `title` becomes its YouTube chapter name."""
        self.log("chapter", name, title=title)

    def sfx(self, name, offset=0.0, gain=None):
        self.log("sfx", name)
        self.add_sound(str(SFX / f"{name}.wav"), time_offset=offset, gain=gain)

    def adopt(self, parent, mob):
        """Move a freshly animated top-level mobject into a group."""
        self.remove(mob)
        parent.add(mob)

    def discard(self, mob):
        """Remove `mob` for good. Animating a part of it (an arm, the mouth) lifts that part out into the
        scene's own list, and Scene.remove() only drops the listed mobjects, so remove the whole family."""
        self.remove(*mob.get_family())

    def top_level(self):
        """Top-level mobjects, excluding the channel watermark (it never shakes or fades with a scene)."""
        mark = getattr(self, "mark", None)
        return [m for m in self.mobjects
                if m is not mark and not any(m is not o and m in o.get_family() for o in self.mobjects)]

    def watermark(self):
        # A bigger head than the avatar's, so only a thin orange rim shows at this size.
        icon = channel_icon(size=256, height=0.42, head_height=6.8, head_y=-0.14)
        mark = Group(icon, wordmark(size=19, color=WHITE)).arrange(RIGHT, buff=0.12)
        mark = flatten(mark, opacity=0.42)
        # Shorts and Reels draw their own buttons in the corners; the top centre stays clear.
        return mark.to_edge(UP, buff=1.0) if VERTICAL else mark.to_corner(UR, buff=0.21)

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

    def voice(self, text, captioned=False):
        """Queue a spoken line at the current time; returns its length in seconds.

        `captioned` says the words are on screen while they are spoken (most viewers watch muted).
        """
        if not VOICE_ENABLED:
            return 0.0
        clip = self.narrator.clip(text)
        self.add_sound(str(clip))
        spoken = self.narrator.duration(clip)
        self.log("speech", text, spoken, captioned=captioned, words=len(text.split()))
        return spoken

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
        spoken = self.voice(speech, captioned=True)
        if hold is None:
            # Long enough to read too: qc.py wants words / 3 seconds on screen (hold + 0.45s of grow and fade).
            hold = max(spoken + 0.4, len(text.split()) / 3 - 0.45) if spoken else 0.8 + 0.3 * len(text.split())
        # On screen from the start of the grow (0.25s) to the end of the fade out (0.2s).
        self.log("text", " ".join(text.split()), hold + 0.45, words=len(text.split()))
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
        hw, hh = config.frame_width / 2, config.frame_height / 2
        planets = VGroup(
            Circle(radius=3.2, fill_color="#232756", fill_opacity=1, stroke_width=0).move_to([-hw - 0.09, hh + 0.2, 0]),
            Circle(radius=4.0, fill_color="#20244F", fill_opacity=1, stroke_width=0).move_to([hw + 0.49, -hh - 0.6, 0]),
        )
        rng = np.random.default_rng(4)
        stars = VGroup(*[
            Dot([rng.uniform(-1, 1) * (hw - 0.11), rng.uniform(-1, 1) * hh, 0], radius=rng.uniform(0.012, 0.03),
                color=WHITE, fill_opacity=rng.uniform(0.15, 0.4))
            for _ in range(70)
        ])
        return VGroup(sky, planets, stars)

    def shadow(self, mob):
        """Soft drop shadow to lift panels off the background."""
        return mob.copy().set_fill(BLACK, 0.35).set_stroke(width=0).shift(DR * 0.08)

    def make_code(self, source, width=None):
        def build(src):
            return Code(
                code_string=src, language="python", formatter_style="one-dark",
                background="window", paragraph_config={"font": MONO},
            )

        # Same scale for every listing of a video, so edited code keeps its font size.
        reference = build(self.code_reference or source)
        return build(source).scale((width or self.code_width) / reference.width)

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

    def error_banner(self, title, message):
        """Red error box, e.g. ("IndexError:", ["list index out of range"]); `message` is a list of lines."""
        box = RoundedRectangle(
            width=pick(11.2, 7.4), height=pick(2.3, 2.9), corner_radius=0.2,
            fill_color="#B00020", fill_opacity=0.97, stroke_color=WHITE, stroke_width=5,
        )
        err = VGroup(
            Text(title, font=MONO, weight=BOLD, font_size=52, color=WHITE),
            *[Text(line, font=MONO, font_size=38, color=WHITE) for line in message],
        ).arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to(box)
        return VGroup(box, err).rotate(-3 * DEGREES)

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

    # ------------------------------------------------- building blocks for videos
    def shocked_bit(self, scale=1.0):
        """Bit with an open mouth, worried brows and a sweat drop."""
        bit = Bit().scale(scale)
        bit.mouth.become(bit.make_mouth("open"))
        bit.brows.become(bit.make_brows("worried"))
        bit.add(bit.sweat_drop())
        return bit

    def knocked_bit(self, scale=1.0):
        """Bit knocked out: crossed eyes and an open mouth."""
        bit = Bit().scale(scale)
        for knocked_out in (bit.x_eyes(), bit.set_mouth("open")):
            knocked_out.begin()
            knocked_out.finish()
        return bit

    def stand(self, bit, point):
        """Move Bit so that he stands on `point`."""
        return bit.shift(np.array(point) - bit.get_bottom())

    def hop(self, bit, point, run_time=0.3, sound="pop"):
        """Jump Bit along an arc so that he lands on `point`."""
        target = bit.get_center() + np.array(point) - bit.get_bottom()
        if sound:
            self.sfx(sound, gain=-4)
        arc = -PI / 2 if target[0] >= bit.get_x() else PI / 2  # always over the top
        self.play(bit.animate(path_arc=arc).move_to(target), run_time=run_time)

    def title_intro(self, title, speech):
        """The series opening: Bit types `title` on a laptop, says it (`speech`) and puts the laptop away.

        Returns (bit, title); the title stays on screen for the caller to clear.
        """
        final = Text(title, font=FONT, weight=BOLD, font_size=pick(120, 80), color=HEADLINE)
        if final.width > config.frame_width - 1.0:
            final.scale_to_fit_width(config.frame_width - 1.0)
        final.move_to(UP * pick(2.0, 3.0))
        bit = Bit().move_to(DOWN * 1.7)
        laptop = self.laptop()
        laptop.shift(UP * (-2.45 - laptop[1].get_top()[1]))  # lid hides Bit's belly, hands rest on its edge

        self.sfx("whoosh")
        self.play(FadeIn(bit, shift=UP * 1.5), FadeIn(laptop, shift=UP * 1.5), run_time=0.5,
                  rate_func=rate_functions.ease_out_back)
        self.play(bit.look(DOWN), run_time=0.2)
        cursor = Rectangle(width=0.07, height=final.height * 1.1, fill_color=TEXT_LIGHT, fill_opacity=1, stroke_width=0)
        self.add(cursor.move_to([final.get_left()[0], final.get_y(), 0]))
        for k, letter in enumerate(final):
            self.sfx("key", gain=-2 if k % 3 else 0)
            cursor.move_to([letter.get_right()[0] + 0.12, final.get_y(), 0])
            tap = Succession(bit.arm_to(k % 2, 34, run_time=0.06), bit.arm_to(k % 2, Bit.REST, run_time=0.06))
            self.play(FadeIn(letter, scale=1.4), tap, run_time=0.12)
        self.remove(cursor, *final)
        self.add(final)
        self.sfx("ding")
        self.play(final.animate(rate_func=there_and_back).scale(1.06), bit.look(ORIGIN), bit.express("grin", "smug"),
                  run_time=0.35)
        self.moment("topic")
        spoken = self.voice(speech, captioned=True)  # the title is on screen
        self.play(bit.talk(max(spoken, 0.5)))
        self.sfx("whoosh")
        self.play(FadeOut(laptop, shift=DOWN * 2), run_time=0.4, rate_func=rush_into)
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        return bit, final

    def hook_open(self, question, speech, sound="crash", shake=True):
        """Cold open for Shorts: hook_visual() is already on the very first frame, then the question.

        `question` is two lines; the second one, in yellow, carries the twist.
        """
        visual = self.hook_visual()
        self.add(visual)
        self.moment("hook")
        self.sfx(sound)
        if shake:
            self.shake(strength=0.2, times=5)
        else:
            self.play(visual.animate(rate_func=there_and_back).scale(1.04), run_time=0.3)
        hook = VGroup(
            Text(question[0], font=FONT, weight=BOLD, font_size=50, color=TEXT_LIGHT),
            Text(question[1], font=FONT, weight=BOLD, font_size=64, color=ACCENT),
        ).arrange(DOWN, buff=0.2)
        if hook.width > config.frame_width - 0.6:
            hook.scale_to_fit_width(config.frame_width - 0.6)
        self.sfx("whoosh", gain=-6)
        self.play(FadeIn(hook.move_to(UP * 3.9), shift=DOWN * 0.3), run_time=0.25)
        spoken = self.voice(speech, captioned=True)
        hold = max(spoken, 1.6) + 0.3
        words = " ".join(question)
        self.log("text", words, 0.25 + hold + 0.3, words=len(words.split()))  # fade in, hold, fade out
        self.wait(hold)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.3)
        self.stage()

    def hook_look(self, bit):
        """loop_back() finale: fade back to the first frame (the background and hook_visual())."""
        return [FadeIn(Group(self.background(), self.hook_visual()))]

    def console(self, width, height=1.95):
        """Dark OUTPUT panel; console_print() writes lines into its `rows`."""
        panel = RoundedRectangle(width=width, height=height, corner_radius=0.15, fill_color="#11111B", fill_opacity=1,
                                 stroke_color=GRAY_D, stroke_width=2)
        label = Text("OUTPUT", font=MONO, font_size=20, color=GRAY_B).next_to(panel.get_corner(UL), DR, buff=0.15)
        box = VGroup(self.shadow(panel), panel, label)
        box.rows = VGroup()
        return box

    def console_print(self, console, text, color=CONSOLE_GREEN, run_time=0.2, font_size=30):
        line = Text(text, font=MONO, font_size=font_size, color=color)
        line.next_to(console[2], DOWN, buff=0.12 + 0.36 * font_size / 30 * len(console.rows), aligned_edge=LEFT)
        self.sfx("blip")
        self.play(FadeIn(line, shift=UP * 0.15), run_time=run_time)
        if console.rows not in self.mobjects:
            self.add(console.rows)
        self.adopt(console.rows, line)

    def terminal(self, width, height, title="bash", font_size=26):
        """Terminal window with a title bar; term_type() and term_echo() write into it and scroll it."""
        body = RoundedRectangle(width=width, height=height, corner_radius=0.18, fill_color="#0E1020", fill_opacity=1,
                                stroke_color="#3A3F75", stroke_width=2)
        bar = Line(body.get_corner(UL) + DOWN * 0.44, body.get_corner(UR) + DOWN * 0.44, stroke_color="#3A3F75",
                   stroke_width=2)
        lights = VGroup(*[Dot(radius=0.07, color=c) for c in ("#FF5F56", "#FFBD2E", "#27C93F")]).arrange(RIGHT, buff=0.12)
        lights.move_to(body.get_corner(UL) + np.array([0.42, -0.22, 0]))
        label = Text(title, font=MONO, font_size=20, color=GRAY_B).move_to(body.get_top() + DOWN * 0.22)
        term = VGroup(self.shadow(body), body, bar, lights, label)
        term.rows, term.font_size = [], font_size  # rows: the lines on screen, top to bottom
        return term

    def _term_row(self, term, k):
        """Left end of row k of the terminal (rows are spaced by the font size)."""
        step = 0.42 * term.font_size / 26
        return term[1].get_corner(UL) + np.array([0.28, -0.44 - 0.12 - step * (k + 0.5), 0]), step

    def _term_room(self, term):
        """Scroll the terminal up by one row when it is full."""
        _, step = self._term_row(term, 0)
        if len(term.rows) >= int((term[1].height - 0.6) / step):
            first = term.rows.pop(0)
            self.play(FadeOut(first, shift=UP * step), *[r.animate.shift(UP * step) for r in term.rows], run_time=0.15)

    def term_type(self, term, command, prompt="$"):
        """Type `command` after the prompt, two characters a frame, with key clicks."""
        self._term_room(term)
        line = Text(f"{prompt} {command}", font=MONO, font_size=term.font_size, color=TEXT_LIGHT)
        n = len(prompt)
        line[:n].set_color(CONSOLE_GREEN)
        line.move_to(self._term_row(term, len(term.rows))[0], aligned_edge=LEFT)
        self.add(line[:n])
        for k in range(n, len(line), 2):
            self.sfx("key", gain=-4 if k % 4 else -1)
            self.play(FadeIn(line[k:k + 2]), run_time=0.06)
        self.remove(*line)
        self.add(line)
        term.rows.append(line)
        return line

    def term_echo(self, term, text, color=TEXT_MUTED, run_time=0.15):
        """Print an output line in the terminal."""
        self._term_room(term)
        line = Text(text, font=MONO, font_size=term.font_size, color=color)
        line.move_to(self._term_row(term, len(term.rows))[0], aligned_edge=LEFT)
        self.play(FadeIn(line, shift=UP * 0.1), run_time=run_time)
        term.rows.append(line)
        return line

    def term_clear(self, term):
        if term.rows:
            self.play(*[FadeOut(r) for r in term.rows], run_time=0.2)
        term.rows = []

    def cheat_sheet(self, bit, title, rows, at=RIGHT * 0.7 + DOWN * 0.1):
        """Recap screen for the long video: every command with a one-line description, to pause and screenshot."""
        self.chapter("cheat_sheet", "Cheat sheet")
        self.say(bit, "Here's your cheat sheet.\nPause and screenshot it!", UR)
        cells = VGroup(*[
            VGroup(Text(cmd, font=MONO, weight=BOLD, font_size=24, color=ACCENT),
                   Text(desc, font=FONT, font_size=22, color=TEXT_LIGHT)).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
            for cmd, desc in rows
        ]).arrange_in_grid(rows=(len(rows) + 1) // 2, cols=2, buff=(0.9, 0.24), flow_order="dr", cell_alignment=LEFT)
        head = headline_text(title, 48, HEADLINE)
        sheet = VGroup(head, cells).arrange(DOWN, buff=0.35)
        panel = RoundedRectangle(width=sheet.width + 0.8, height=sheet.height + 0.6, corner_radius=0.25,
                                 fill_color="#20244F", fill_opacity=1, stroke_color="#3A3F75", stroke_width=3)
        card = VGroup(self.shadow(panel), panel, sheet.move_to(panel))
        card.scale(min(12.2 / card.width, 6.6 / card.height)).move_to(at)  # as big as the frame allows
        self.sfx("whoosh")
        self.play(FadeIn(card[:2], scale=0.95), FadeIn(head), run_time=0.4)
        for cell in cells:
            self.sfx("blip", gain=-8)
            self.play(FadeIn(cell, shift=RIGHT * 0.2), run_time=0.15)
        self.sfx("ding")
        self.play(bit.express("grin", "raised"), bit.arms_up(run_time=0.3), run_time=0.3)
        self.wait(2.5)
        self.play(bit.arms_rest(run_time=0.3), bit.express("smile", "neutral"), run_time=0.3)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def joke(self, bit, setup, punch, speech_setup=None, speech_punch=None):
        """Setup line, then the punchline with a rimshot; Bit ends up grinning."""
        self.say(bit, setup, UR, speech=speech_setup)
        bubble = self.say(bit, punch, UR, keep=True, speech=speech_punch)
        self.moment("joke")
        self.play(bit.express("grin", "raised"), run_time=0.15)
        self.sfx("rimshot_ba")
        self.sfx("rimshot_dum", offset=0.18)
        self.sfx("rimshot_tss", offset=0.4)
        self.wait(1.0)
        self.play(FadeOut(bubble, scale=0.9), run_time=0.2)

    def subscribe_button(self, subscribed=False):
        """Red SUBSCRIBE pill, or the grey SUBSCRIBED one plus its check mark (returned apart, to draw it in)."""
        pill = RoundedRectangle(width=4.0, height=1.0, corner_radius=0.5, stroke_width=0, fill_opacity=1,
                                fill_color="#3B3F63" if subscribed else "#E53935")
        if not subscribed:
            return VGroup(pill, Text("SUBSCRIBE", font=FONT, weight=BOLD, font_size=38).move_to(pill))
        label = Text("SUBSCRIBED", font=FONT, weight=BOLD, font_size=34, color=TEXT_LIGHT)
        check = VMobject().set_points_as_corners([[-0.15, 0.0, 0], [-0.04, -0.12, 0], [0.17, 0.13, 0]])
        check.set_stroke(CONSOLE_GREEN, 9).set_cap_style(CapStyleType.ROUND)
        VGroup(check, label).arrange(RIGHT, buff=0.22).move_to(pill)
        return VGroup(pill, label), check

    def subscribe_card(self):
        """Channel card (avatar, name, tagline) above the SUBSCRIBE button; returns (card, button)."""
        avatar = channel_icon(size=256, height=1.0, head_height=6.8, head_y=-0.14)
        info = VGroup(
            wordmark(size=40),
            Text("Code, explained bit by bit", font=FONT, font_size=22, color=TEXT_MUTED),
        ).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        button = self.subscribe_button()
        content = Group(Group(avatar, info).arrange(RIGHT, buff=0.3), button).arrange(DOWN, buff=0.35)
        panel = RoundedRectangle(width=content.width + 0.7, height=content.height + 0.6, corner_radius=0.3,
                                 fill_color="#262A52", fill_opacity=1, stroke_color="#3A3F75", stroke_width=2)
        panel.move_to(content)
        return Group(self.shadow(panel), panel, content), button

    def pulse(self, button, times=2):
        """The button breathes and sends out a ripple, to pull the eye to it."""
        beats = []
        for _ in range(times):
            ring = button[0].copy().set_fill(opacity=0).set_stroke("#FF6B6B", 6)
            beats.append(AnimationGroup(
                button.animate(rate_func=there_and_back).scale(1.06),
                ring.animate(remover=True).scale(1.25).set_stroke(opacity=0),
                run_time=0.7,
            ))
        return Succession(*beats)

    def confetti(self, mob, count=40, run_time=1.1):
        """Confetti bursting out of `mob`'s edge."""
        rng = np.random.default_rng(3)
        pieces = []
        for _ in range(count):
            angle = rng.uniform(0, TAU)
            out = np.array([np.cos(angle), np.sin(angle), 0])
            start = mob.get_center() + out * [mob.width / 2, mob.height / 2, 0]
            piece = Rectangle(width=0.22, height=0.11, stroke_width=0, fill_opacity=1,
                              fill_color=rng.choice([ACCENT, HEADLINE, *FRAME_COLORS])).move_to(start)
            piece.rotate(rng.uniform(0, PI))
            piece.spun = 0.0
            travel = out * rng.uniform(1.2, 2.6) + DOWN * 0.4

            # Fly out fast and slow down, staying bright until the very end.
            def fly(m, alpha, start=start, travel=travel, spin=rng.uniform(-2 * PI, 2 * PI)):
                eased = rate_functions.ease_out_cubic(alpha)
                m.rotate(spin * eased - m.spun)
                m.spun = spin * eased
                m.move_to(start + travel * eased).set_fill(opacity=1 - alpha ** 3)

            pieces.append(UpdateFromAlphaFunc(piece, fly, remover=True))
        return AnimationGroup(*pieces, run_time=run_time)

    def ending(self, lines, closing, loop_line=None, loop_finale=None):
        """Takeaway headline (`lines`), channel card and a SUBSCRIBE click while Bit says `closing`.

        Shorts then end on `loop_line`, a beat that leads back into the cold open (see loop_back).
        """
        headline = VGroup(*[Text(line, font=FONT, weight=BOLD, font_size=56, color=HEADLINE) for line in lines])
        headline.arrange(DOWN, buff=0.2).to_edge(UP, buff=pick(0.9, 2.0))
        bit = Bit().move_to(pick([-3.6, -1.0, 0], [0, -2.8, 0]))
        card, button = self.subscribe_card()
        card.move_to(pick([3.0, -0.9, 0], [0, 1.75, 0]))

        self.play(Write(headline), FadeIn(bit, shift=UP * 0.5), run_time=1.0)
        self.moment("cta")
        self.play(FadeIn(card, scale=0.9), run_time=0.4)
        self.say(bit, closing, UR, gesture=self.pulse(button))

        cursor = Polygon([0, 0, 0], [0.0, -0.75, 0], [0.2, -0.56, 0], [0.42, -0.95, 0], [0.55, -0.88, 0],
                         [0.34, -0.5, 0], [0.6, -0.48, 0], fill_color=WHITE, fill_opacity=1,
                         stroke_color=INK, stroke_width=3).move_to(pick([6.2, -3.4, 0], [3.2, -4.8, 0]))
        self.play(FadeIn(cursor), bit.look(pick(RIGHT, UP)), run_time=0.3)
        self.play(cursor.animate.move_to(button.get_center() + DR * 0.3), run_time=0.7)

        # Click: the button squashes and a ripple spreads from the cursor tip.
        tip = cursor.get_vertices()[0]
        ripple = Circle(radius=0.12, stroke_color=WHITE, stroke_width=5).move_to(tip)
        self.sfx("pop")
        self.play(button.animate(rate_func=there_and_back).scale(0.9),
                  ripple.animate.scale(4).set_stroke(opacity=0), run_time=0.25)
        self.remove(ripple)

        # Subscribed: grey pill with a check mark, confetti, and a cheering Bit.
        done, check = self.subscribe_button(subscribed=True)
        Group(done, check).move_to(button)
        self.sfx("ding")
        self.sfx("whoosh", gain=-8)
        # Cross-fade the labels: morphing SUBSCRIBE into SUBSCRIBED letter by letter turns to mush.
        self.play(Transform(button[0], done[0], run_time=0.3), button[1].animate(run_time=0.15).set_opacity(0),
                  FadeIn(done[1], scale=1.2, run_time=0.3), self.confetti(button),
                  bit.express("grin", "raised", run_time=0.3), bit.look(ORIGIN, run_time=0.3), bit.arms_up(run_time=0.3),
                  cursor.animate(run_time=0.5).shift(DR * 0.6).set_opacity(0))
        self.play(Create(check), bit.animate(rate_func=there_and_back).shift(UP * 0.4), run_time=0.35)
        if SHORT and loop_line:
            self.loop_back(bit, loop_line, loop_finale)
            return
        self.play(bit.wave(i=0), bit.arm_to(1, Bit.REST, run_time=0.3), bit.express("smile", "neutral"))
        self.play(bit.blink())
        self.wait(0.8)
        self.play(*[FadeOut(m) for m in [*self.top_level(), self.mark]], run_time=0.8)

    def loop_back(self, bit, line, finale=None):
        """Shorts replay by themselves: Bit says `line`, then the picture turns into the cold open's.

        `finale(bit)` returns the animations that end on the first frame's look (default: crash_look).
        """
        self.play(bit.arms_rest(run_time=0.25), bit.express("flat", "worried", run_time=0.25))
        self.moment("loop")
        self.say(bit, line, UR)
        self.sfx("whoosh")
        self.play(*(finale or self.crash_look)(bit), run_time=0.3)

    def crash_look(self, bit):
        """Red glow and a knocked-out Bit: the first frame of a video that opens on a crash."""
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0)
        return [glow.animate.set_fill(opacity=0.2), bit.x_eyes(), bit.set_mouth("open")]


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


def headline_text(text, size, color):
    """Thumbnail lettering: heavy Poppins with a thick ink outline, readable at phone size."""
    return Text(text, font=FONT, weight=BOLD, font_size=size, color=color).set_stroke(INK, size / 7, background=True)


class ThumbnailMixin:
    """Mix in before a video's scene for its YouTube thumbnail (1280x720); subclasses draw it in design().

        class Thumbnail(ThumbnailMixin, MyVideo): ...
        .venv/bin/manim -s -r 1280,720 my_video.py Thumbnail
    """

    def render(self, preview=False):
        return Scene.render(self, preview)  # a still: no timeline or audio mastering

    def construct(self):
        self.camera.background_color = BG
        self.add(self.background())
        self.design()
