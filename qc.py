"""Quality check for the rendered videos; re-renders whatever a fresh render can fix.

    .venv/bin/python qc.py                     # every video, both formats
    .venv/bin/python qc.py recursion           # one video
    .venv/bin/python qc.py --format vertical   # one format
    .venv/bin/python qc.py --fix               # re-render missing/stale/broken outputs, then check again

Exits with 1 while any check fails. Reports and contact sheets (for the visual checklist in
CLAUDE.md) are written to media/qc/<video>/.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
LIBRARY = ROOT / "bitbybit.py"
QC_DIR = ROOT / "media" / "qc"
BG = np.array([0x1B, 0x1E, 0x3C])

# One entry per video: its source file and the scene to render.
VIDEOS = {
    "recursion": {"file": "recursion.py", "scene": "Recursion"},
    "off_by_one": {"file": "off_by_one.py", "scene": "OffByOne"},
    "binary_search": {"file": "binary_search.py", "scene": "BinarySearch"},
    "aliasing": {"file": "aliasing.py", "scene": "Aliasing"},
    "floating_point": {"file": "floating_point.py", "scene": "FloatingPoint"},
    "hash_map": {"file": "hash_map.py", "scene": "HashMap"},
}

FORMATS = {
    "wide": {
        "size": (1920, 1080), "folder": "1080p30", "env": {},
        "duration": (None, 600),       # (warn above, fail above) in seconds
        "silence": (3.5, 6.0),         # longest pause in the soundtrack: (warn above, fail above)
        "hook": False,                 # first frame must already show the scene
        "mark": (0.84, 0.0, 0.995, 0.12),  # watermark box as fractions of the frame: x0, y0, x1, y1
        "sheet_every": 5,
        # Engagement, from the render's timeline (warn above, fail above), in seconds.
        "hook_by": None,               # first on-screen words must come this early (Shorts only)
        "topic_by": (10, 15),          # the topic must be named this early
        "promise_by": 15,              # ...and a reason to keep watching (moment 'promise'; YouTube only)
        "loop": False,                 # must end on a moment 'loop' that leads back into the opening (Shorts)
        "chapters": True,              # write YouTube chapters for the description
        "dead_air": (4.0, 7.0),        # longest stretch with nothing said, shown or heard that is new
        "interrupt_every": (30, 45),   # longest stretch without a new chapter or key moment
        "cta_tail": (12, 20),          # from the subscribe call to the end
    },
    "vertical": {
        "size": (1080, 1920), "folder": "1920p30", "env": {"BIT_FORMAT": "vertical"},
        "duration": (75, 90),
        "silence": (2.5, 4.0),
        "hook": True,
        "mark": (0.35, 0.05, 0.65, 0.125),
        "sheet_every": 3,
        "hook_by": 2.0,
        "topic_by": (8, 12),
        "promise_by": None,
        "loop": True,
        "chapters": False,
        "dead_air": (2.5, 4.0),
        "interrupt_every": (20, 30),
        "cta_tail": (10, 15),
    },
}

WPM = (120, 200)              # narration speed, words per minute
SPEECH_SHARE = (0.3, 0.85)    # share of the runtime with narration
READING_WPS = 3.0             # a bubble stays up at least words / READING_WPS seconds
SURPRISES = {"gag", "surprise", "joke"}

FPS = 30
LUFS_TARGET, LUFS_TOLERANCE, MAX_PEAK = -14.0, 1.5, -1.0
MAX_AUDIO_GAP = 5.0       # the soundtrack may stop this long before the picture (final fade)
MAX_FREEZE = 6.0          # a picture that does not change for longer is worth a look
HOOK_CONTENT = 0.08       # share of the first frame that must differ from the plain background
MARK_COVERAGE = 0.95      # share of sampled frames that must show the watermark


class Report:
    def __init__(self):
        self.checks = []

    def add(self, name, ok, detail, fixable=False, warn=False):
        status = "PASS" if ok else ("WARN" if warn else "FAIL")
        self.checks.append({"name": name, "status": status, "detail": detail, "fixable": fixable and status == "FAIL"})

    @property
    def failed(self):
        return [c for c in self.checks if c["status"] == "FAIL"]

    @property
    def fixable(self):
        return [c for c in self.failed if c["fixable"]]


def run(cmd, text=True):
    return subprocess.run(cmd, capture_output=True, text=text)


def probe(movie):
    out = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,duration",
               "-show_entries", "format=duration", "-of", "json", str(movie)]).stdout
    info = json.loads(out)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    return video, audio, float(info["format"]["duration"])


def loudness(movie):
    log = run(["ffmpeg", "-nostats", "-i", str(movie), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    summary = log[log.rindex("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"True peak:\s+Peak:\s+(-?[\d.inf]+) dBFS", summary).group(1))
    return lufs, peak


def longest_silence(movie, audio_end):
    log = run(["ffmpeg", "-nostats", "-i", str(movie), "-vn", "-af", "silencedetect=noise=-50dB:d=1",
               "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    # A silence still open at the end of the soundtrack is the final fade, not a pause.
    gaps = [(s, e) for s, e in zip(starts, ends) if e < audio_end - 0.05]
    return max(gaps, key=lambda g: g[1] - g[0], default=None)


def longest_freeze(movie):
    log = run(["ffmpeg", "-nostats", "-i", str(movie), "-an", "-vf", "scale=320:-2,freezedetect=n=-60dB:d=2",
               "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
    lengths = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", log)]
    return max(zip(lengths, starts), default=None)


def frames(movie, size, every=1.0):
    """Frames sampled every `every` seconds (from t=0), scaled to `size`, as an (n, h, w, 3) array."""
    w, h = size
    raw = run(["ffmpeg", "-v", "error", "-i", str(movie), "-vf", f"fps=1/{every}:start_time=0,scale={w}:{h}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], text=False).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def first_frame(movie, size):
    w, h = size
    raw = run(["ffmpeg", "-v", "error", "-i", str(movie), "-frames:v", "1", "-vf", f"scale={w}:{h}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], text=False).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def has_watermark(frame, box):
    """The watermark's orange disc shows as reddish pixels inside its box."""
    h, w, _ = frame.shape
    x0, y0, x1, y1 = box
    region = frame[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].astype(int)
    r, g, b = region[..., 0], region[..., 1], region[..., 2]
    return np.count_nonzero((r > 90) & (r - g > 35) & (r - b > 35)) >= 0.01 * r.size


def contact_sheet(samples, every, path):
    n = len(samples)
    h, w, _ = samples[0].shape
    cols = 10 if w < h else 6
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 6), rows * (h + 22)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(samples):
        x, y = (i % cols) * (w + 6), (i // cols) * (h + 22)
        draw.text((x + 3, y + 4), f"{i * every:.0f}s", fill="black")
        sheet.paste(Image.fromarray(frame), (x, y + 20))
    sheet.save(path)


def check(name, fmt):
    video_cfg, spec = VIDEOS[name], FORMATS[fmt]
    source = ROOT / video_cfg["file"]
    movie = ROOT / "media" / "videos" / source.stem / spec["folder"] / f"{video_cfg['scene']}.mp4"
    out_dir = QC_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = Report()

    # The video's code is its own file plus the shared library it imports.
    sources = [source] + ([LIBRARY] if "from bitbybit import" in source.read_text() else [])
    no_cache = any("config.disable_caching = True" in s.read_text() for s in sources)
    rep.add("Cache manim đã tắt", no_cache, "có config.disable_caching = True" if no_cache
            else "thiếu config.disable_caching = True: âm thanh có thể mất hoặc lệch hình")
    if not movie.exists():
        rep.add("Có file video", False, f"chưa có {movie.relative_to(ROOT)}", fixable=True)
        return movie, rep
    rep.add("Có file video", True, str(movie.relative_to(ROOT)))
    changed = [s.name for s in sources if s.stat().st_mtime > movie.stat().st_mtime]
    rep.add("Video mới hơn code", not changed, "khớp với code hiện tại" if not changed
            else f"{', '.join(changed)} đã sửa sau lần render cuối", fixable=True)

    video, audio, duration = probe(movie)
    num, den = map(int, video["r_frame_rate"].split("/"))
    shape = (int(video["width"]), int(video["height"]))
    rep.add("Độ phân giải / fps", shape == spec["size"] and num / den == FPS,
            f"{shape[0]}x{shape[1]} @ {num / den:g}fps (cần {spec['size'][0]}x{spec['size'][1]} @ {FPS})", fixable=True)

    warn_at, fail_at = spec["duration"]
    rep.add("Độ dài", duration <= fail_at and (warn_at is None or duration <= warn_at),
            f"{duration:.1f}s (cảnh báo > {warn_at}s, lỗi > {fail_at}s)" if warn_at else f"{duration:.1f}s",
            warn=duration <= fail_at)

    if audio is None:
        rep.add("Có âm thanh", False, "video không có luồng âm thanh", fixable=True)
    else:
        audio_end = float(audio["duration"])
        gap = duration - audio_end
        rep.add("Âm thanh đủ tới cuối", gap <= MAX_AUDIO_GAP,
                f"âm thanh dừng trước hình {gap:.1f}s (tối đa {MAX_AUDIO_GAP:g}s)", fixable=True)
        lufs, peak = loudness(movie)
        rep.add("Độ to (LUFS)", abs(lufs - LUFS_TARGET) <= LUFS_TOLERANCE,
                f"{lufs:.1f} LUFS (cần {LUFS_TARGET:g} ± {LUFS_TOLERANCE:g})", fixable=True)
        rep.add("Đỉnh âm (true peak)", peak <= MAX_PEAK, f"{peak:.1f} dBTP (tối đa {MAX_PEAK:g})", fixable=True)
        silence = longest_silence(movie, audio_end)
        length = silence[1] - silence[0] if silence else 0.0
        warn_at, fail_at = spec["silence"]
        where = f" ở {silence[0]:.1f}–{silence[1]:.1f}s" if silence else ""
        rep.add("Khoảng lặng dài nhất", length <= warn_at,
                f"{length:.1f}s{where} (cảnh báo > {warn_at:g}s, lỗi > {fail_at:g}s)", warn=length <= fail_at)

    freeze = longest_freeze(movie)
    length = freeze[0] if freeze else 0.0
    rep.add("Hình đứng yên lâu nhất", length <= MAX_FREEZE,
            f"{length:.1f}s" + (f" từ {freeze[1]:.1f}s" if freeze else "") + f" (cảnh báo > {MAX_FREEZE:g}s)", warn=True)

    small = (spec["size"][0] // 3, spec["size"][1] // 3)
    first = first_frame(movie, small)
    content = np.mean(np.abs(first.astype(int) - BG).sum(axis=-1) > 60)
    rep.add("Khung đầu có nội dung (hook)", content >= HOOK_CONTENT,
            f"{content:.0%} khung hình khác nền (cần ≥ {HOOK_CONTENT:.0%})", warn=not spec["hook"])

    samples = frames(movie, small)
    body = samples[: max(1, int(duration - 1.5))]  # the watermark fades out with the last scene
    coverage = np.mean([has_watermark(f, spec["mark"]) for f in body])
    rep.add("Watermark luôn hiện", coverage >= MARK_COVERAGE,
            f"có trong {coverage:.0%} khung hình mẫu (cần ≥ {MARK_COVERAGE:.0%})")

    every = spec["sheet_every"]
    contact_sheet(samples[::every], every, out_dir / f"{fmt}_sheet.png")

    timeline = movie.with_suffix(".timeline.json")
    if timeline.exists() and timeline.stat().st_mtime >= movie.stat().st_mtime - 60:
        timeline = json.loads(timeline.read_text())
        engagement(rep, timeline, spec)
        if spec["chapters"]:
            lines = youtube_chapters(timeline)
            (out_dir / f"{fmt}_chapters.txt").write_text("\n".join(lines) + "\n")
            rep.add("[Thu hút] Mốc chương cho YouTube", len(lines) >= 3,
                    f"{len(lines)} chương → {(out_dir / f'{fmt}_chapters.txt').relative_to(ROOT)}"
                    if len(lines) >= 3 else f"chỉ có {len(lines)} chương (YouTube cần ≥ 3, mỗi chương ≥ 10s)", warn=True)
    else:
        rep.add("[Thu hút] Có dòng thời gian", False, f"thiếu {timeline.name} của lần render này", fixable=True)
    return movie, rep


def graded(rep, name, value, limits, detail, unit="s"):
    """Add a check that warns above limits[0] and fails above limits[1]."""
    warn_at, fail_at = limits
    rep.add(name, value <= warn_at, f"{detail} (cảnh báo > {warn_at:g}{unit}, lỗi > {fail_at:g}{unit})",
            warn=value <= fail_at)


def engagement(rep, timeline, spec):
    """Checks on pacing and structure that keep viewers watching."""
    events, end = timeline["events"], timeline["duration"]
    at = {e["label"]: e["t"] for e in reversed(events) if e["kind"] == "moment"}  # first occurrence wins
    speech = [e for e in events if e["kind"] == "speech"]
    texts = [e for e in events if e["kind"] == "text"]

    if spec["hook_by"] is not None:
        first_words = min((e["t"] for e in texts), default=end)
        ok = at.get("hook", end) <= 0.5 and first_words <= spec["hook_by"]
        rep.add("[Thu hút] Hook ngay đầu video", ok,
                f"cảnh hook lúc {at.get('hook', float('nan')):.1f}s, câu hỏi trên màn hình lúc {first_words:.1f}s "
                f"(cần hook ở 0s, chữ trước {spec['hook_by']:g}s)")

    topic = at.get("topic", end)
    graded(rep, "[Thu hút] Nêu chủ đề sớm", topic, spec["topic_by"], f"chủ đề được nêu lúc {topic:.1f}s")
    if spec["promise_by"] is not None:
        promise = at.get("promise")
        rep.add("[Thu hút] Hứa hẹn lý do xem tiếp", promise is not None and promise <= spec["promise_by"],
                f"lúc {promise:.1f}s (cần trước {spec['promise_by']:g}s)" if promise is not None
                else "không có moment 'promise'")

    rep.add("[Thu hút] Có cao trào (payoff)", "payoff" in at,
            f"cao trào lúc {at['payoff']:.1f}s ({at['payoff'] / end:.0%} video)" if "payoff" in at
            else "không có khoảnh khắc payoff nào")
    funny = sorted((t, k) for k, t in at.items() if k in SURPRISES)
    rep.add("[Thu hút] Có bất ngờ / hài hước", bool(funny),
            ", ".join(f"{k} lúc {t:.1f}s" for t, k in funny) or "không có gag, surprise hay joke")

    # Dead air: time after the previous beat (or the end of its speech) before anything new happens.
    worst, where, busy_until = 0.0, 0.0, 0.0
    for e in sorted(events, key=lambda e: e["t"]):
        if e["t"] - busy_until > worst:
            worst, where = e["t"] - busy_until, busy_until
        busy_until = max(busy_until, e["t"] + (e["duration"] if e["kind"] == "speech" else 0.0))
    graded(rep, "[Thu hút] Khoảng không có gì mới", worst, spec["dead_air"], f"{worst:.1f}s từ {where:.1f}s")

    marks = sorted([0.0, end] + [e["t"] for e in events if e["kind"] in ("chapter", "moment")])
    gap, start = max((b - a, a) for a, b in zip(marks, marks[1:]))
    graded(rep, "[Thu hút] Đổi cảnh / điểm nhấn thường xuyên", gap, spec["interrupt_every"],
           f"lâu nhất {gap:.1f}s từ {start:.1f}s")

    if "cta" in at:
        # On Shorts the loop beat after the call is content again, so the call ends where it starts.
        stop = at.get("loop", end)
        graded(rep, "[Thu hút] Kêu gọi đăng ký ngắn, ở cuối", stop - at["cta"], spec["cta_tail"],
               f"từ {at['cta']:.1f}s tới {'cảnh nối vòng' if 'loop' in at else 'hết video'}: {stop - at['cta']:.1f}s")
    else:
        rep.add("[Thu hút] Kêu gọi đăng ký ngắn, ở cuối", False, "không có lời kêu gọi đăng ký (moment 'cta')")
    if spec["loop"]:
        rep.add("[Thu hút] Kết thúc nối vòng về đầu", "loop" in at and end - at["loop"] <= 6,
                f"cảnh nối vòng lúc {at['loop']:.1f}s, video hết lúc {end:.1f}s" if "loop" in at
                else "không có moment 'loop' ở cuối video", warn=True)

    silent = [e["label"] for e in speech if not e.get("captioned")]
    rep.add("[Thu hút] Xem không tiếng vẫn hiểu", not silent,
            "mọi câu đọc đều có chữ trên màn hình" if not silent else f"câu đọc không có chữ: {silent}")

    if speech:
        talking = sum(e["duration"] for e in speech)
        wpm = sum(e["words"] for e in speech) / talking * 60
        rep.add("[Thu hút] Tốc độ đọc", WPM[0] <= wpm <= WPM[1], f"{wpm:.0f} từ/phút (nên {WPM[0]}–{WPM[1]})",
                warn=True)
        share = talking / end
        rep.add("[Thu hút] Tỉ lệ có lời dẫn", SPEECH_SHARE[0] <= share <= SPEECH_SHARE[1],
                f"{share:.0%} thời lượng (nên {SPEECH_SHARE[0]:.0%}–{SPEECH_SHARE[1]:.0%})", warn=True)
    # The timeline rounds to 0.01s.
    rushed = [e["label"] for e in texts if e["duration"] + 0.01 < e["words"] / READING_WPS]
    rep.add("[Thu hút] Đủ thời gian đọc chữ", not rushed,
            "mọi bong bóng đủ lâu để đọc" if not rushed else f"hiện quá nhanh: {rushed}", warn=True)


def youtube_chapters(timeline):
    """Chapter lines for a YouTube description: they must start at 0:00, be 3+ and each last 10s+."""
    chapters = [(e["t"], e["title"]) for e in timeline["events"] if e["kind"] == "chapter" and e.get("title")]
    merged = []
    for t, title in chapters:
        if merged and t - merged[-1][0] < 10:  # too short for YouTube: fold into the previous chapter
            continue
        merged.append((0.0 if not merged else t, title))
    if merged and timeline["duration"] - merged[-1][0] < 10:
        merged.pop()
    return [f"{int(t // 60)}:{int(t % 60):02d} {title}" for t, title in merged]


def render(name, fmt):
    video_cfg, spec = VIDEOS[name], FORMATS[fmt]
    log = QC_DIR / name / f"{fmt}_render.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(ROOT / ".venv" / "bin" / "manim"), "-qh", "--fps", str(FPS), video_cfg["file"], video_cfg["scene"]]
    print(f"  ... đang render: {' '.join(f'{k}={v}' for k, v in spec['env'].items())} {' '.join(cmd[1:])}", flush=True)
    with log.open("w") as f:
        done = subprocess.run(cmd, cwd=ROOT, env={**os.environ, **spec["env"]}, stdout=f, stderr=subprocess.STDOUT)
    if done.returncode:
        print(f"  !!! render lỗi (exit {done.returncode}), xem {log.relative_to(ROOT)}")
    return done.returncode == 0


def show(name, fmt, movie, rep):
    print(f"\n{name} · {fmt}  ({movie.relative_to(ROOT)})")
    for c in rep.checks:
        print(f"  {c['status']:<4}  {c['name']:<44} {c['detail']}")
    verdict = "KHÔNG ĐẠT" if rep.failed else "ĐẠT"
    print(f"  => {verdict}")
    for c in rep.failed:
        hint = "render lại sẽ sửa được (--fix)" if c["fixable"] else "cần sửa code rồi render lại"
        print(f"     - {c['name']}: {hint}")
    report = QC_DIR / name / f"{fmt}_report.json"
    report.write_text(json.dumps({"video": name, "format": fmt, "movie": str(movie.relative_to(ROOT)),
                                  "passed": not rep.failed, "checks": rep.checks}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Kiểm tra chất lượng video đã render.")
    parser.add_argument("videos", nargs="*", help=f"mặc định: tất cả ({', '.join(VIDEOS)})")
    parser.add_argument("--format", choices=FORMATS, help="mặc định: cả hai tỉ lệ")
    parser.add_argument("--fix", action="store_true", help="render lại khi lỗi có thể sửa bằng render")
    args = parser.parse_args()
    unknown = set(args.videos) - set(VIDEOS)
    if unknown:
        parser.error(f"video không có trong VIDEOS: {', '.join(sorted(unknown))}")

    all_passed = True
    for name in args.videos or VIDEOS:
        for fmt in [args.format] if args.format else FORMATS:
            movie, rep = check(name, fmt)
            # One re-render fixes anything caused by a stale or broken render; a second attempt never helps.
            if args.fix and rep.fixable:
                show(name, fmt, movie, rep)
                if render(name, fmt):
                    movie, rep = check(name, fmt)
            show(name, fmt, movie, rep)
            sheet = QC_DIR / name / f"{fmt}_sheet.png"
            if movie.exists() and sheet.exists():
                print(f"  ảnh lưới để duyệt bằng mắt: {sheet.relative_to(ROOT)}")
            all_passed &= not rep.failed
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
