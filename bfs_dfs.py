"""BFS vs DFS on San Francisco's real road network, and what the two searches sound like (Shorts/Reels only).

Two maps side by side, the same streets (OpenStreetMap), the same start (Golden Gate Bridge) and goal
(Oracle Park). The code underneath is one search loop; the only difference is q.popleft() (a queue: BFS)
or q.pop() (a stack: DFS). They race at the same pace: BFS spreads in rings, DFS dives down one road
and finds the goal first, having checked thousands fewer intersections... then the routes appear, and
DFS's is hundreds of miles long. Every number on screen comes from running the searches on the map.

The soundtrack is the searches themselves (Sonifier): every visit plays a note, BFS climbing the scale ring
by ring, DFS rising and falling with its distance to the goal, over a soft drone with no beat. The synthwave
track (make_track()) is off: `music = False`. The map lives in assets/maps/ (built once from an Overpass
download, see build_map()). Timing follows a 120 BPM grid; the video rewinds to its first frame, so the
replay loops seamlessly.

Render:   BIT_FORMAT=vertical .venv/bin/manim -qh -r 1080,1920 --fps 60 bfs_dfs.py BfsDfs
Preview:  BIT_FORMAT=vertical .venv/bin/manim -ql --fps 30 bfs_dfs.py BfsDfs
Cover:    BIT_FORMAT=vertical .venv/bin/manim -s -r 1080,1920 -o Thumbnail_vertical bfs_dfs.py Thumbnail
Map:      .venv/bin/python bfs_dfs.py build <overpass.json>   (the query is in build_map()'s docstring)
"""

import gzip
import heapq
import math
import sys
from collections import defaultdict, deque

import cairo
import soundfile as sf
from scipy import signal
from scipy.ndimage import gaussian_filter

from bitbybit import *
from bitbybit import _save, _t_axis

MAP_FILE = ROOT / "assets" / "maps" / "san_francisco.json.gz"
ICONS = ROOT / "assets" / "icons"
START = ("Golden Gate Bridge", 37.8065, -122.4745)
GOAL = ("Oracle Park", 37.7785, -122.3895)
LANDMARKS = [("Golden Gate Park", 37.7694, -122.4862), ("Twin Peaks", 37.7544, -122.4477), ("Coit Tower", 37.8024, -122.4058)]
KM_PER_MILE = 1.609344

BPM = 120
BEAT = 60 / BPM
LENGTH = 48  # beats: 12 bars, three rounds of the chords, so the loop comes back in time and on the same chord
# Sections, in beats: intro, build, drop (the race), break (the routes), drop 2, outro.
INTRO, BUILD, DROP, BREAK, DROP2, OUTRO = 0, 4, 8, 24, 32, 40

CODE = """q = deque([start])
while q:
    u = q.popleft()
    if u in seen: continue
    seen.add(u)
    if u == goal: break
    q.extend(roads[u])"""
POP_LINE = 2

BFS_C, DFS_C = "#4FC3F7", "#FF9F43"
PANEL_BG, PANEL_EDGE = "#12152B", "#2E3366"
ROAD = ["#262B52", "#343A6B", "#4A5190"]  # minor, middle, major roads

# Layout of the 8 x 14.2 frame, top to bottom: title, headline, the stats line, the two maps with their
# counters, the code panel (Bit in its corner), the caption bar, the attribution. The bottom quarter
# (y < -3.55) stays clear for the app's buttons; the watermark sits in the bottom-right corner.
TITLE_Y, HEADLINE_Y, STATS_Y = 5.95, 5.35, 4.72
HEAD_Y, MAP_TOP, MAP_BOTTOM = 4.22, 3.92, -0.12
MAP_W, MAP_X = 3.75, (-1.95, 1.95)
CODE_TOP, CODE_BOTTOM = -0.32, -2.82
CAPTION_Y = -3.2
NOTE_Y = -3.85


def snap(t):
    """Move fast on the beat, then hold: motion is over by 60% of the tick."""
    return rate_functions.ease_out_cubic(min(1.0, t / 0.6))


# ------------------------------------------------------------------- the map
def build_map(raw_path):
    """Turn an Overpass download of the city's drivable roads into assets/maps/: intersections and roads.

    The download (about 19 MB):
        [out:json][timeout:180];
        way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|
            trunk_link|primary_link|secondary_link|tertiary_link|living_street)$"](37.705,-122.52,37.835,-122.355);
        (._;>;); out body;
    Nodes between intersections are folded into their road's shape; one-ways count both ways; only the
    largest connected piece is kept.
    """
    raw = json.loads(Path(raw_path).read_text())
    pos = {e["id"]: (e["lat"], e["lon"]) for e in raw["elements"] if e["type"] == "node"}
    ways = [e for e in raw["elements"] if e["type"] == "way"]
    rank_of = {"motorway": 2, "trunk": 2, "primary": 2, "secondary": 1, "tertiary": 1}
    nbr, seg_rank, ends = defaultdict(set), {}, set()
    for w in ways:
        ns, r = w["nodes"], rank_of.get(w["tags"].get("highway", "").replace("_link", ""), 0)
        ends.update((ns[0], ns[-1]))
        for a, b in zip(ns, ns[1:]):
            if a != b:
                nbr[a].add(b)
                nbr[b].add(a)
                seg_rank[min(a, b), max(a, b)] = max(r, seg_rank.get((min(a, b), max(a, b)), 0))
    junctions = {n for n in nbr if len(nbr[n]) != 2 or n in ends}
    roads = {}
    for s in junctions:
        for n in nbr[s]:
            chain, prev, cur = [s], s, n
            while cur not in junctions:
                chain.append(cur)
                prev, cur = cur, next(x for x in nbr[cur] if x != prev)
            chain.append(cur)
            if cur == s:
                continue
            key = (min(s, cur), max(s, cur))
            km = sum(haversine(pos[a], pos[b]) for a, b in zip(chain, chain[1:]))
            if key not in roads or km < roads[key][0]:
                rank = max(seg_rank[min(a, b), max(a, b)] for a, b in zip(chain, chain[1:]))
                roads[key] = (km, rank, chain if s < cur else chain[::-1])
    adj = defaultdict(set)
    for a, b in roads:
        adj[a].add(b)
        adj[b].add(a)
    keep, done = set(), set()
    for n in adj:
        if n not in done:
            piece, todo = {n}, [n]
            while todo:
                for v in adj[todo.pop()]:
                    if v not in piece:
                        piece.add(v)
                        todo.append(v)
            done |= piece
            keep = max(keep, piece, key=len)
    out = {"nodes": {str(n): [round(pos[n][0], 6), round(pos[n][1], 6)] for n in keep},
           "roads": [[a, b, round(km, 5), rank, [[round(pos[c][0], 5), round(pos[c][1], 5)] for c in chain[1:-1]]]
                     for (a, b), (km, rank, chain) in roads.items() if a in keep]}
    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(MAP_FILE, "wt") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"{MAP_FILE}: {len(out['nodes'])} intersections, {len(out['roads'])} roads")


def haversine(p, q):
    """Distance in km between two (lat, lon) points."""
    (la1, lo1), (la2, lo2) = p, q
    r = math.pi / 180
    d = math.sin((la2 - la1) * r / 2) ** 2 + math.cos(la1 * r) * math.cos(la2 * r) * math.sin((lo2 - lo1) * r / 2) ** 2
    return 12742 * math.asin(math.sqrt(d))


class RoadMap:
    """The city as a graph: intersections (lat, lon), roads (length, rank, shape) and each one's neighbours.

    Neighbours are listed in ascending OSM id order, the order DFS pushes them in.
    """

    def __init__(self):
        with gzip.open(MAP_FILE, "rt") as f:
            data = json.load(f)
        self.pos = {int(k): tuple(v) for k, v in data["nodes"].items()}
        self.roads, adj = {}, defaultdict(list)
        for a, b, km, rank, mid in data["roads"]:
            self.roads[a, b] = (km, rank, [self.pos[a], *map(tuple, mid), self.pos[b]])
            adj[a].append(b)
            adj[b].append(a)
        self.adj = {n: sorted(vs) for n, vs in adj.items()}

    def nearest(self, lat, lon):
        k = math.cos(math.radians(lat))
        return min(self.pos, key=lambda n: (self.pos[n][0] - lat) ** 2 + ((self.pos[n][1] - lon) * k) ** 2)

    def shape(self, a, b):
        """The (lat, lon) points of the road from a to b."""
        pts = self.roads[min(a, b), max(a, b)][2]
        return pts if a < b else pts[::-1]

    def km(self, a, b):
        return self.roads[min(a, b), max(a, b)][0]

    def search(self, start, goal, dfs):
        """The loop on screen, with q.pop() for DFS: returns the visit order [(node, parent)] and the route."""
        q, seen, order, parent = deque([(start, None)]), set(), [], {}
        while q:
            u, p = q.pop() if dfs else q.popleft()
            if u in seen:
                continue
            seen.add(u)
            order.append((u, p))
            parent[u] = p
            if u == goal:
                break
            q.extend((v, u) for v in self.adj[u] if v not in seen)
        route = [goal]
        while parent[route[-1]] is not None:
            route.append(parent[route[-1]])
        return order, route[::-1]

    def dijkstra(self, start, goal):
        """The shortest route in miles, for comparison."""
        best, todo = {start: 0.0}, [(0.0, start)]
        while todo:
            d, u = heapq.heappop(todo)
            if u == goal:
                return d / KM_PER_MILE
            if d > best[u]:
                continue
            for v in self.adj[u]:
                nd = d + self.km(u, v)
                if nd < best.get(v, math.inf):
                    best[v] = nd
                    heapq.heappush(todo, (nd, v))

    def miles(self, route):
        return sum(self.km(a, b) for a, b in zip(route, route[1:])) / KM_PER_MILE


def rgb(color, alpha=1.0):
    r, g, b = color_to_rgb(color)
    return r, g, b, alpha


class MapView:
    """One map panel, drawn with cairo at the video's resolution: the streets, the search tree growing over
    them (its newest edges glowing) and the route. frame() returns the RGBA picture for an ImageMobject."""

    def __init__(self, city, order, route, color, width, height):
        ppu = config.pixel_width / config.frame_width
        self.w, self.h, self.ppu = round(width * ppu), round(height * ppu), ppu
        self.city, self.order, self.route, self.color = city, order, route, color
        lats = [p[0] for p in city.pos.values()]
        lons = [p[1] for p in city.pos.values()]
        self.kx = math.cos(math.radians((min(lats) + max(lats)) / 2))
        span_x, span_y = (max(lons) - min(lons)) * self.kx, max(lats) - min(lats)
        self.scale = min((self.w - 0.3 * ppu) / span_x, (self.h - 0.9 * ppu) / span_y)
        self.cx, self.cy = (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2
        self.base = self.surface()
        ctx = self.context(self.base)
        self.panel_path(ctx)
        ctx.set_source_rgba(*rgb(PANEL_BG))
        ctx.fill()
        for rank in range(3):
            self.stroke(ctx, [self.px(pts) for km, r, pts in city.roads.values() if r == rank], ROAD[rank],
                        (0.007, 0.011, 0.018)[rank])
        self.tree, self.trail = self.surface(), self.surface()
        self.k = self.m = 0
        self.tree_alpha = 1.0

    def surface(self):
        return cairo.ImageSurface(cairo.FORMAT_ARGB32, self.w, self.h)

    def context(self, s):
        ctx = cairo.Context(s)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        return ctx

    def panel_path(self, ctx):
        r = 0.12 * self.ppu
        ctx.new_sub_path()
        for x, y, a in ((self.w - r, r, -PI / 2), (self.w - r, self.h - r, 0), (r, self.h - r, PI / 2), (r, r, PI)):
            ctx.arc(x, y, r, a, a + PI / 2)
        ctx.close_path()

    def px(self, pts):
        return [((lon - self.cx) * self.kx * self.scale + self.w / 2, (self.cy - lat) * self.scale + self.h / 2 + 0.1 * self.ppu)
                for lat, lon in pts]

    def point(self, lat, lon, center):
        """Scene coordinates of (lat, lon) on this map, drawn around `center`."""
        (x, y), = self.px([(lat, lon)])
        return np.array([center[0] + (x - self.w / 2) / self.ppu, center[1] - (y - self.h / 2) / self.ppu, 0])

    def stroke(self, ctx, polylines, color, width, alpha=1.0):
        for line in polylines:
            ctx.move_to(*line[0])
            for p in line[1:]:
                ctx.line_to(*p)
        ctx.set_source_rgba(*rgb(color, alpha))
        ctx.set_line_width(width * self.ppu)
        ctx.stroke()

    def edges(self, pairs):
        return [self.px(self.city.shape(p, u)) for u, p in pairs if p is not None]

    def grow(self, k):
        """Show the first k visits of the search tree (redrawn from scratch when going back)."""
        k = int(min(k, len(self.order)))
        if k < self.k:
            self.tree, self.k = self.surface(), 0
        if k > self.k:
            self.stroke(self.context(self.tree), self.edges(self.order[self.k:k]), self.color, 0.011, 0.75)
            self.k = k

    def draw_route(self, m):
        """Show the first m roads of the route."""
        m = int(min(m, len(self.route) - 1))
        if m < self.m:
            self.trail, self.m = self.surface(), 0
        if m > self.m:
            pairs = [(self.route[i + 1], self.route[i]) for i in range(self.m, m)]
            ctx = self.context(self.trail)
            self.stroke(ctx, self.edges(pairs), self.color, 0.05, 0.5)
            self.stroke(ctx, self.edges(pairs), "#FFFFFF", 0.018, 0.95)
            self.m = m

    def frame(self):
        out = self.surface()
        ctx = cairo.Context(out)
        ctx.set_source_surface(self.base)
        ctx.paint()
        self.panel_path(ctx)
        ctx.clip()
        ctx.set_source_surface(self.tree)
        ctx.paint_with_alpha(self.tree_alpha)
        if 0 < self.k < len(self.order):  # the frontier glows while the search runs
            hot = self.surface()
            self.stroke(self.context(hot), self.edges(self.order[max(0, self.k - 260):self.k]), "#FFFFFF", 0.022, 0.9)
            glow = np.ndarray((self.h, self.w, 4), np.uint8, hot.get_data(), strides=(hot.get_stride(), 4, 1))
            glow = gaussian_filter(glow.astype(np.float32), (0.025 * self.ppu, 0.025 * self.ppu, 0)) * 1.6
            tint = np.array([*color_to_rgb(self.color)[::-1], 1.0], np.float32)  # BGRA: the glow takes the map's colour
            glow = np.clip(glow * tint, 0, 255).astype(np.uint8)
            layer = cairo.ImageSurface.create_for_data(memoryview(np.ascontiguousarray(glow)), cairo.FORMAT_ARGB32, self.w, self.h)
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_surface(layer)
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.set_source_surface(hot)
            ctx.paint_with_alpha(0.55)
        ctx.set_source_surface(self.trail)
        ctx.paint()
        out.flush()
        bgra = np.ndarray((self.h, self.w, 4), np.uint8, out.get_data(), strides=(out.get_stride(), 4, 1))
        return bgra[..., [2, 1, 0, 3]].copy()


# ---------------------------------------------------------------- the track
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def saw(hz, n, phase=0.0):
    """A band-limited sawtooth (polyBLEP)."""
    dt = hz / SR
    ph = (phase + dt * np.arange(n)) % 1.0
    s = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt
    s[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt
    s[m] -= x * x + x + x + 1
    return s


def lowpass(x, hz, order=2):
    return signal.sosfilt(signal.butter(order, min(hz, SR * 0.45) / (SR / 2), output="sos"), x)


def highpass(x, hz, order=2):
    return signal.sosfilt(signal.butter(order, hz / (SR / 2), btype="high", output="sos"), x)


def bandpass(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos"), x)


def sweep_filter(x, f0, f1, kind="low"):
    """A filter whose cutoff glides from f0 to f1 (exponentially), in 20 ms steps."""
    out, zi, step = np.zeros_like(x), None, int(SR * 0.02)
    for i in range(0, x.size, step):
        f = f0 * (f1 / f0) ** (i / max(1, x.size - 1))
        sos = signal.butter(2, min(f, SR * 0.45) / (SR / 2), btype=kind, output="sos")
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        out[i:i + step], zi = signal.sosfilt(sos, x[i:i + step], zi=zi)
    return out


def env(n, attack=0.005, decay=None, release=0.0):
    """Attack, then exponential decay (time constant `decay`) or a hold, then a linear release at the end."""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(attack, 1e-4))
    if decay:
        e = e * np.exp(-t / decay)
    if release:
        r = int(release * SR)
        e[-r:] *= np.linspace(1, 0, r)
    return e


# Am F C G, one bar each: pads (MIDI), bass root, and the arpeggio's notes.
CHORDS = [((57, 60, 64, 69), 33), ((53, 57, 60, 65), 29), ((55, 60, 64, 67), 36), ((55, 59, 62, 67), 31)]
# The hook in the drops, 8 beats in eighths (MIDI, None = rest), over Am F then C G.
HOOK = [76, None, 74, 72, None, 69, None, 72, 74, None, 72, 69, None, 67, 69, None,
        76, None, 79, 76, None, 74, 72, None, 74, None, None, 72, 69, None, None, None]


class Mix:
    """A stereo mix of LENGTH beats: buses that sum into the track."""

    def __init__(self):
        self.n = int(LENGTH * BEAT * SR)
        self.bus = defaultdict(lambda: np.zeros((2, self.n)))

    def put(self, bus, sig, t, pan=0.0, gain=1.0):
        s = int(round(t * SR))
        if s >= self.n:
            return
        sig = sig[:self.n - s] * gain
        self.bus[bus][0, s:s + sig.size] += sig * math.sqrt((1 - pan) / 2)
        self.bus[bus][1, s:s + sig.size] += sig * math.sqrt((1 + pan) / 2)


def section(b):
    return ("intro" if b < BUILD else "build" if b < DROP else "drop" if b < BREAK else "break" if b < DROP2
            else "drop" if b < OUTRO else "outro")


def make_track(path):
    """The music: a 120 BPM synthwave track, mixed and written as one stereo file.

    Intro (filtered pad and arpeggio, soft hats), build (kick, a snare roll, a riser, the filter opening,
    a half-beat breath), the drop for the race (four-on-the-floor kick, big clap, sixteenth hats with open
    hats, offbeat bass, supersaw pads and the arpeggio pumping under the kick, the hook in its second half),
    the break for the routes (no drums, a sub bass, a riser into drop 2), drop 2 (everything, hook from the
    start), the outro (lighter, the filter closing) and a tape stop on the last beat, under the rewind.
    """
    rng = np.random.default_rng(5)
    mix = Mix()
    kicks = []

    # Drums.
    t = np.arange(int(0.45 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(48 + 140 * np.exp(-t * 28)) / SR) * np.exp(-t * 5.5)
    kick[:220] += highpass(rng.normal(size=220), 3000) * np.exp(-np.arange(220) / 25) * 0.6
    kick = np.tanh(kick * 1.8)
    n = int(0.3 * SR)
    noise = rng.normal(size=n)
    bursts = sum(np.roll(np.exp(-np.arange(n) / (SR * 0.006)), int(d * SR)) for d in (0, 0.011, 0.022))
    clap = bandpass(noise, 900, 5000) * (bursts * 0.7 + np.exp(-np.arange(n) / (SR * 0.07)))
    hat = highpass(rng.normal(size=int(0.04 * SR)), 7000) * env(int(0.04 * SR), 0.001, 0.012)
    ohat = highpass(rng.normal(size=int(0.2 * SR)), 6500) * env(int(0.2 * SR), 0.001, 0.07)
    n = int(0.18 * SR)
    snare = bandpass(rng.normal(size=n), 1500, 7000) * env(n, 0.001, 0.05) + np.sin(2 * np.pi * 190 * np.arange(n) / SR) * env(n, 0.001, 0.04)

    for q in range(LENGTH * 4):  # sixteenths
        b, pos, tq = q / 4, q % 4, q / 4 * BEAT
        sec = section(b)
        swing = 0.012 if pos % 2 else 0.0
        if pos == 0 and (sec in ("drop", "outro") or (sec == "build" and b < DROP - 0.5)):
            mix.put("kick", kick, tq, gain=0.75 if sec == "build" else 1.0)
            kicks.append(tq)
        if sec == "drop" and pos == 0 and int(b) % 2:
            mix.put("clap", clap, tq, gain=0.55)
        if sec in ("drop", "outro"):
            mix.put("hat", hat, tq + swing, pan=0.25, gain=(0.5 if pos == 0 else 0.3) * (0.7 if sec == "outro" else 1))
            if pos == 2:
                mix.put("hat", ohat, tq, pan=-0.2, gain=0.3)
        elif sec in ("intro", "build", "break") and pos == 2:
            mix.put("hat", hat, tq, pan=0.25, gain=0.25)
        # Snare rolls into the drops: eighths, then sixteenths, swelling, with a half-beat breath before the drop.
        for top in (DROP, DROP2):
            if top - 4 <= b < top - 0.5 and (pos % 2 == 0 or b >= top - 2):
                mix.put("snare", snare, tq, gain=0.12 + 0.4 * (b - top + 4) / 3.5)

    # Bass, pads, arpeggio and hook, chord by chord.
    for bar in range(LENGTH // 4):
        b0 = bar * 4
        sec = section(b0)
        notes, root = CHORDS[bar % 4]
        t0, dur = b0 * BEAT, 4 * BEAT
        pad_cut = {"intro": 700, "build": 700, "drop": 4200, "break": 2200, "outro": 2200}[sec]
        for note in notes:
            n = int((dur + 0.4) * SR)
            for k, cents in enumerate((-22, -13, -5, 0, 5, 13, 22)):
                voice = saw(midi(note) * 2 ** (cents / 1200), n, rng.random()) * env(n, 0.08, release=0.45)
                if sec == "build":
                    voice = sweep_filter(voice, 700, 5000)
                else:
                    voice = lowpass(voice, pad_cut)
                mix.put("pad", voice, t0, pan=-0.85 + 1.7 * k / 6, gain=0.05)
        if sec in ("drop", "outro", "build"):
            for beat in range(4):  # offbeat eighths, an octave pair
                n = int(0.22 * SR)
                tone = (saw(midi(root + 12), n) + 0.5 * saw(midi(root + 12) * 1.005, n)) * env(n, 0.003, 0.09)
                tone = lowpass(tone, 1100) + 0.8 * np.sin(2 * np.pi * midi(root) * np.arange(n) / SR) * env(n, 0.003, 0.12)
                mix.put("bass", tone, t0 + (beat + 0.5) * BEAT, gain=0.45 if sec != "build" else 0.25)
        else:  # a long sub note
            n = int(dur * SR)
            sub = np.sin(2 * np.pi * midi(root + 12) * np.arange(n) / SR) * env(n, 0.3, release=0.3)
            mix.put("bass", sub, t0, gain=0.35 if sec == "break" else 0.2)
        tones = [notes[1], notes[2], notes[3], notes[1] + 12, notes[2] + 12, notes[3], notes[2], notes[1] + 12]
        arp_cut = {"intro": 900, "build": 1500, "drop": 3800, "break": 3000, "outro": 1800}[sec]
        for i in range(16):
            n = int(0.2 * SR)
            hz = midi(tones[i % 8])
            pluck = (saw(hz, n) + 0.4 * np.sign(np.sin(2 * np.pi * hz * 2 * np.arange(n) / SR))) * env(n, 0.002, 0.07)
            mix.put("arp", lowpass(pluck, arp_cut + (2000 * i / 16 if sec == "build" else 0)), t0 + i * BEAT / 4,
                    pan=0.3 if i % 2 else -0.3, gain=0.09)
        hook_on = (sec == "drop" and (b0 >= DROP + 8 or b0 >= DROP2))
        if hook_on:
            for i in range(16):
                note = HOOK[(bar % 2) * 16 + i]
                if note is None:
                    continue
                length = 1 + next((j for j in range(1, 4) if i + j < 16 and HOOK[(bar % 2) * 16 + i + j] is None), 0)
                n = int((length * BEAT / 2) * SR)
                hz = midi(note) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * np.arange(n) / SR) * np.minimum(1, np.arange(n) / (0.15 * SR)))
                ph = np.cumsum(hz) / SR
                lead = (2 * (ph % 1) - 1) * 0.6 + np.sign(np.sin(2 * np.pi * ph)) * 0.4
                lead = lowpass(lead, 3800) * env(n, 0.01, release=0.06)
                mix.put("lead", lead, t0 + i * BEAT / 2, gain=0.16)

    # Risers into the drops, and an impact (sub boom and crash) on each drop.
    for top in (DROP, DROP2):
        d = 4 * BEAT
        n = int(d * SR)
        rise = sweep_filter(rng.normal(size=n), 400, 9000, "high") * np.linspace(0, 1, n) ** 2
        rise += np.sin(2 * np.pi * np.cumsum(np.geomspace(200, 1600, n)) / SR) * np.linspace(0, 1, n) ** 3 * 0.3
        mix.put("fx", rise, (top - 4) * BEAT, gain=0.18)
        n = int(1.6 * SR)
        boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-np.arange(n) / (0.08 * SR))) / SR) * np.exp(-np.arange(n) / (0.5 * SR))
        crash = highpass(rng.normal(size=n), 4000) * np.exp(-np.arange(n) / (0.6 * SR))
        mix.put("fx", boom * 0.8 + crash * 0.25, top * BEAT)

    # The pump: pads, bass, arpeggio and hook duck under every kick.
    t = np.arange(mix.n) / SR
    duck = np.ones(mix.n)
    for k in kicks:
        s = int(k * SR)
        seg = t[s:s + int(0.4 * SR)] - k
        duck[s:s + seg.size] = np.minimum(duck[s:s + seg.size], 1 - 0.75 * np.exp(-seg / 0.1) * np.minimum(1, seg / 0.004 + 0.2))
    for name in ("pad", "bass", "arp", "lead"):
        mix.bus[name] *= duck * (0.6 if name == "lead" else 1) + (0.4 if name == "lead" else 0)

    # The breath: everything but the snare roll and the riser drops out half a beat before each drop.
    for top in (DROP, DROP2):
        a, b = int((top - 0.5) * BEAT * SR), int(top * BEAT * SR)
        for name in ("pad", "bass", "arp", "lead", "hat"):
            mix.bus[name][:, a:b] *= 0.05

    # Echoes and space: a ping-pong dotted-eighth delay on the arpeggio and hook, a room on clap, snare and hook.
    for name in ("arp", "lead"):
        dry, d = mix.bus[name].copy(), int(0.75 * BEAT * SR)
        for k in range(1, 4):
            shifted = np.zeros_like(dry)
            shifted[:, d * k:] = dry[:, :-d * k] if k % 2 == 0 else dry[::-1, :-d * k]
            mix.bus[name] += shifted * 0.38 ** k
    n = int(1.8 * SR)
    ir = np.stack([lowpass(rng.normal(size=n), 6000) * np.exp(-np.arange(n) / (0.45 * SR)) for _ in range(2)])
    ir[:, :int(0.02 * SR)] = 0
    send = mix.bus["clap"] * 0.6 + mix.bus["snare"] * 0.4 + mix.bus["lead"] * 0.35 + mix.bus["arp"] * 0.2
    wet = np.stack([signal.fftconvolve(send[c], ir[c])[:mix.n] for c in range(2)])
    wet *= 0.25 / (np.max(np.abs(wet)) or 1) * np.max(np.abs(send))

    levels = {"kick": 0.9, "clap": 0.8, "hat": 0.6, "snare": 0.7, "bass": 0.9, "pad": 0.75, "arp": 0.7, "lead": 0.8, "fx": 0.7}
    track = sum(mix.bus[name] * g for name, g in levels.items()) + wet * 3
    track = highpass(track, 28)

    # Tape stop on the last beat: the music winds down under the rewind.
    s = int((LENGTH - 1) * BEAT * SR)
    speed = np.linspace(1, 0, mix.n - s) ** 1.5
    src = s + np.cumsum(speed)
    for c in range(2):
        track[c, s:] = np.interp(src, np.arange(mix.n), track[c]) * np.linspace(1, 0.2, mix.n - s)

    track = np.tanh(track / np.max(np.abs(track)) * 1.6) / np.tanh(1.6) * 0.9  # glue: a soft clip
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), track.T, SR, subtype="PCM_16")


TRACK = SFX / "bfs_dfs_track.wav"


def make_bfs_sfx():
    """One-shots on top of the music: a pin drop, the two "found" chimes, the odometer tick, a sad trombone."""
    rng = np.random.default_rng(9)
    t = _t_axis(0.25)
    _save("bd_pin", np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 18) + 300) / SR) * np.exp(-t * 16), 0.4)
    for name, notes in (("bd_found_bfs", (1046.5, 1568.0)), ("bd_found_dfs", (1174.7, 1760.0))):
        out = np.zeros(int(SR * 1.0))
        for i, hz in enumerate(notes):
            tt = _t_axis(0.8)
            bell = sum(a * np.sin(2 * np.pi * hz * r * tt) * np.exp(-tt * 4 * k) for r, a, k in ((1, 1, 1), (2.76, 0.3, 2), (5.4, 0.1, 3)))
            s = int(i * BEAT / 4 * SR)
            out[s:s + bell.size] += bell[:out.size - s]
        _save(name, out, 0.5)
    t = _t_axis(0.03)
    _save("bd_tick", highpass(rng.normal(size=t.size), 2500) * np.exp(-t * 200) + np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 250) * 0.4, 0.3)
    # Sad trombone: three short falling notes and a long wobbling fourth.
    parts = []
    for hz, d in ((233.1, 0.28), (220.0, 0.28), (207.7, 0.28), (196.0, 0.9)):
        tt = _t_axis(d)
        f = hz * (1 + (0.025 * np.sin(2 * np.pi * 6 * tt) * np.minimum(1, tt / 0.2) if d > 0.5 else 0))
        ph = np.cumsum(f) / SR
        brass = 2 * (ph % 1) - 1
        brass = sweep_filter(brass, 600, 2200 if d < 0.5 else 900) * env(tt.size, 0.03, release=0.08)
        parts.append(brass)
    _save("bd_wah", np.concatenate(parts), 0.5)


# ------------------------------------------------------------- the searches, heard
SCALE = [0, 3, 5, 7, 10]  # A minor pentatonic
TOP = 16  # scale steps the searches climb through (A3 to A6)


def scale_hz(k, base=57):
    """The k-th note of the A minor pentatonic above A3."""
    k = int(np.clip(k, 0, TOP + 4))
    return midi(base + 12 * (k // 5) + SCALE[k % 5])


def bell(hz, length=0.14):
    """BFS's voice: a clear little bell."""
    t = _t_axis(length)
    tone = (np.sin(2 * np.pi * hz * t) + 0.25 * np.sin(2 * np.pi * 2.76 * hz * t) * np.exp(-t * 40)
            + 0.1 * np.sin(2 * np.pi * 5.4 * hz * t) * np.exp(-t * 60))
    return tone * np.minimum(1, t / 0.002) * np.exp(-t * 26)


def pluck(hz, length=0.12):
    """DFS's voice: a warm, slightly gritty pluck."""
    n = int(length * SR)
    return lowpass(saw(hz, n) + 0.5 * saw(hz * 2.005, n), 2600) * env(n, 0.002, 0.035)


class Sonifier:
    """The searches made audible, mixed into one stereo track once the timeline is known.

    A soft drone (no beat) sits under everything; the voices go through a small room.
    """

    def __init__(self, seconds):
        self.seconds = seconds
        self.n = int(seconds * SR)
        self.dry, self.send = np.zeros((2, self.n)), np.zeros((2, self.n))

    def put(self, sig, t, pan=0.0, gain=1.0, room=0.35):
        s = int(round(t * SR))
        if not 0 <= s < self.n:
            return
        sig = sig[:self.n - s] * gain
        for c, side in enumerate((math.sqrt((1 - pan) / 2), math.sqrt((1 + pan) / 2))):
            self.dry[c, s:s + sig.size] += sig * side
            self.send[c, s:s + sig.size] += sig * side * room

    def chord(self, voice, steps, t, pan, gain, spread=BEAT / 8):
        """An arpeggiated chord: the scale steps one after another, `spread` apart."""
        for i, k in enumerate(steps):
            self.put(voice(scale_hz(k), 0.6), t + i * spread, pan, gain)

    def drone(self):
        """Am(add9), dark and still, every partial a whole number of cycles long so the loop is seamless."""
        t = np.arange(self.n) / SR
        out = np.zeros(self.n)
        for note, g in ((45, 1.0), (52, 0.7), (59, 0.45), (60, 0.35), (64, 0.3)):
            for d in (0.9993, 1.0007):  # a slow shimmer, never a pulse
                hz = round(midi(note) * d * self.seconds) / self.seconds
                out += g * (np.sin(2 * np.pi * hz * t) + 0.3 * np.sin(4 * np.pi * hz * t))
        swell = 1 + 0.25 * np.sin(2 * np.pi * t * 2 / self.seconds)  # two slow breaths per loop
        out = lowpass(out * swell, 700)
        return out / np.max(np.abs(out))

    def segment(self):
        from pydub import AudioSegment

        rng = np.random.default_rng(3)
        n = int(2.2 * SR)
        ir = np.stack([lowpass(rng.normal(size=n), 5000) * np.exp(-np.arange(n) / (0.5 * SR)) for _ in range(2)])
        ir[:, :int(0.025 * SR)] = 0
        wet = np.stack([signal.fftconvolve(self.send[c], ir[c])[:self.n] for c in range(2)])
        wet *= 0.5 * np.max(np.abs(self.send)) / (np.max(np.abs(wet)) or 1)
        mix = self.dry + wet
        mix *= 0.8 / (np.max(np.abs(mix)) or 1)
        mix += self.drone()[None, :] * 0.06  # about -24 dB: felt more than heard
        pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
        return AudioSegment(pcm.T.tobytes(), frame_rate=SR, sample_width=2, channels=2)


BD_SFX = ("bd_pin", "bd_found_bfs", "bd_found_dfs", "bd_tick", "bd_wah")


# ---------------------------------------------------------------- icons and text
_TEXTS = {}


def label(text, size, color, font=MONO, weight=BOLD):
    """Text, cached: the counters redraw every frame."""
    key = (text, size, str(color), font, weight)
    if key not in _TEXTS:
        _TEXTS[key] = Text(text, font=font, weight=weight, font_size=size, color=color)
    return _TEXTS[key].copy()


def pin(color):
    glyph = SVGMobject(str(ICONS / "map-marker.svg")).set_stroke(INK, 2.5).set_fill(color, 1)
    return glyph.scale(0.32 / glyph.height)


class BfsDfs(BitScene):
    music = False  # the synthwave track; off: the searches themselves are the soundtrack (Sonifier)

    def setup(self):
        super().setup()
        self.city = RoadMap()
        start, goal = self.city.nearest(*START[1:]), self.city.nearest(*GOAL[1:])
        self.runs = {}
        for name, dfs in (("BFS", False), ("DFS", True)):
            order, route = self.city.search(start, goal, dfs)
            self.runs[name] = {"order": order, "route": route, "checked": len(order), "miles": self.city.miles(route)}
        self.best_miles = self.city.dijkstra(start, goal)
        # What the voices play: BFS climbs with its ring (hops from the start), DFS with how close it is to the goal.
        self.start, self.goal = start, goal
        depth = {}
        for u, p in self.runs["BFS"]["order"]:
            depth[u] = depth[p] + 1 if p is not None else 0
        self.runs["BFS"]["pitch"] = [TOP * depth[u] / depth[goal] for u, p in self.runs["BFS"]["order"]]
        self.runs["DFS"]["pitch"] = [TOP * self.closeness(u) for u, p in self.runs["DFS"]["order"]]
        lons = [lon for lat, lon in self.city.pos.values()]
        self.west, self.east = min(lons), max(lons)

    def closeness(self, node):
        """0 at the start's distance from the goal (or farther), 1 at the goal."""
        far = haversine(self.city.pos[self.start], self.city.pos[self.goal])
        return float(np.clip(1 - haversine(self.city.pos[node], self.city.pos[self.goal]) / far, 0, 1))

    def pan_of(self, node):
        """Where a node sits east-west, as a stereo position."""
        return 0.85 * (2 * (self.city.pos[node][1] - self.west) / (self.east - self.west) - 1)

    # ---------------------------------------------------------------- beat grid
    def tick(self, *anims, beats=1, bit_free=True):
        """Play `anims` from this beat to the next one (or `beats` on), to the exact frame.

        manim rounds every play up to whole frames, so each play aims at its beat's absolute frame
        instead of adding run times. Bit bobs on the beat unless he is busy.
        """
        if bit_free:
            anims += (self.bob(),)
        self.b += beats
        fps = config.frame_rate
        frames = round(self.b * BEAT * fps) - round(self.time * fps)
        self.play(*(anims or (Wait(frozen_frame=False),)), run_time=frames / fps - 1e-4)
        assert round(self.time * fps) == round(self.b * BEAT * fps), "fell off the beat grid"

    def sfx(self, name, offset=0.0, gain=None):
        """Sound effects start on the beat grid, not on the frame manim rounded the tick to."""
        super().sfx(name, offset + self.b * BEAT - self.time, gain)

    def bob(self):
        """Bit squashes on the kick."""
        return self.bit.animate(rate_func=lambda t: there_and_back(min(1.0, t / 0.45))).stretch(0.9, 1, about_edge=DOWN)

    def live(self, mob, step):
        """Call step(dt) every frame for `mob` itself; an animation's copies of it must not redraw themselves."""
        mob.add_updater(lambda m, dt: step(dt) if m is mob else None)

    # ---------------------------------------------------------------- pieces
    def watermark(self):
        # Like the other beat Shorts, the top of the frame is the title: the mark goes to the bottom-right corner.
        return super().watermark().to_corner(DR, buff=0.35)

    def background(self):
        """Near-black navy with a faint dot grid. Oversized so moves never show an edge."""
        sky = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, fill_color="#0D0F22",
                        fill_opacity=1, stroke_width=0)
        dots = VGroup(*[Dot([x, y, 0], radius=0.012, color=WHITE, fill_opacity=0.08)
                        for x in np.arange(-4.75, 4.8, 0.5) for y in np.arange(-7.75, 7.8, 0.5)])
        return Group(sky, flatten(dots))

    def caption(self, text, colors=None):
        """Replace the line in the caption bar; returns the animations."""
        self.close_caption()
        new = Text(text, font=MONO, weight=BOLD, font_size=22, color=TEXT_LIGHT, t2c=colors)
        new.scale(min(1, 7.2 / new.width))
        old, self.cap = self.cap, new.move_to([0, CAPTION_Y, 0])
        self.cap_since = (self.time, text)
        return [FadeOut(old, shift=UP * 0.15, rate_func=lambda t: min(1.0, t / 0.2)),
                FadeIn(new, scale=0.9, rate_func=lambda t: snap(max(0.0, t - 0.2) / 0.8))]

    def close_caption(self):
        if self.cap_since:
            t, text = self.cap_since
            self.events.append({"t": round(t, 2), "kind": "text", "label": text, "duration": round(self.time - t, 2),
                                "words": len(text.split())})
            self.cap_since = None

    def headline(self, text, colors=None):
        """Replace the big line under the title; returns the animations."""
        new = Text(text, font=FONT, weight=BOLD, font_size=40, color=TEXT_LIGHT, t2c=colors)
        new.scale(min(1, 7.4 / new.width)).move_to([0, HEADLINE_Y, 0])
        old, self.head = self.head, new
        return [FadeOut(old, shift=UP * 0.2, rate_func=lambda t: min(1.0, t / 0.25)),
                FadeIn(new, shift=UP * 0.2, rate_func=lambda t: snap(max(0.0, t - 0.15) / 0.85))]

    def counter_text(self, name, value, found=False):
        color = BFS_C if name == "BFS" else DFS_C
        text = f"{value:,}" + (" ✓" if found else "")
        return label(text, 22, color if found else TEXT_LIGHT)

    def make_panel(self, name, x):
        """A map panel: the counter bar, the map picture, its frame, the pins and labels, the footer note."""
        color = BFS_C if name == "BFS" else DFS_C
        run = self.runs[name]
        height = MAP_TOP - MAP_BOTTOM
        center = np.array([x, (MAP_TOP + MAP_BOTTOM) / 2, 0])
        view = MapView(self.city, run["order"], run["route"], color, MAP_W, height)
        picture = ImageMobject(view.frame()).set(width=MAP_W).move_to(center)
        frame = RoundedRectangle(width=MAP_W, height=height, corner_radius=0.12, stroke_color=PANEL_EDGE,
                                 stroke_width=2).move_to(center)
        bar = RoundedRectangle(width=MAP_W, height=0.46, corner_radius=0.08, fill_color=PANEL_BG, fill_opacity=1,
                               stroke_color=PANEL_EDGE, stroke_width=2).move_to([x, HEAD_Y, 0])
        tag = label(name, 20, color).move_to(bar.get_left() + RIGHT * 0.2, aligned_edge=LEFT)
        count = self.counter_text(name, 0).move_to(bar.get_right() + LEFT * 0.2, aligned_edge=RIGHT)
        marks = Group()
        for lname, lat, lon in LANDMARKS:
            p = view.point(lat, lon, center)
            marks.add(VGroup(Dot(p, radius=0.03, color=TEXT_MUTED),
                             label(lname, 11, TEXT_MUTED, weight=NORMAL).next_to(p, DOWN, buff=0.04)))
        for (lname, lat, lon), pc, side in ((START, ACCENT, UP), (GOAL, "#4CD97B", DOWN)):
            p = view.point(lat, lon, center)
            marker = pin(pc).move_to(p, aligned_edge=DOWN)
            text = label(lname, 12, TEXT_LIGHT)
            chip = VGroup(RoundedRectangle(width=text.width + 0.16, height=0.24, corner_radius=0.05, fill_color="#0D0F22",
                                           fill_opacity=0.9, stroke_color=pc, stroke_width=1.5), text)
            text.move_to(chip[0])
            chip.next_to(marker if side is UP else p, side, buff=0.05)
            chip.shift(RIGHT * max(0, x - MAP_W / 2 + 0.05 - chip.get_left()[0]) + LEFT * max(0, chip.get_right()[0] - x - MAP_W / 2 + 0.05))
            marks.add(marker, chip)
        note = label("spreads in rings" if name == "BFS" else "dives down one road", 13, TEXT_MUTED, weight=NORMAL)
        note.move_to(frame.get_corner(DL) + np.array([0.15, 0.17, 0]), aligned_edge=LEFT)
        panel = Group(picture, frame, bar, tag, count, marks, note)
        panel.view, panel.picture, panel.count, panel.bar, panel.note, panel.name = view, picture, count, bar, note, name
        panel.marks = marks
        panel.found = False
        return panel

    def refresh_panel(self, panel):
        """Per frame: grow the search to the race's progress, draw the route so far, update the counter."""
        view, run = panel.view, self.runs[panel.name]
        view.grow(self.race.get_value())
        view.draw_route(self.routes[panel.name].get_value())
        view.tree_alpha = self.dim.get_value()
        panel.picture.pixel_array = view.frame()
        shown = (min(view.k, run["checked"]), view.k >= run["checked"])
        if shown != getattr(panel, "shown", None):
            panel.count.become(self.counter_text(panel.name, *shown).move_to(panel.bar.get_right() + LEFT * 0.2,
                                                                              aligned_edge=RIGHT))
            panel.shown = shown

    def code_panel(self):
        code = Code(code_string=CODE, language="python", formatter_style="one-dark", background="rectangle",
                    add_line_numbers=True, paragraph_config={"font": MONO})
        code.background.set_opacity(0)
        code.scale(min(4.9 / code.width, (CODE_TOP - CODE_BOTTOM - 0.6) / code.height))
        box = RoundedRectangle(width=7.65, height=CODE_TOP - CODE_BOTTOM, corner_radius=0.12, fill_color=PANEL_BG,
                               fill_opacity=1, stroke_color=PANEL_EDGE, stroke_width=2).move_to([0, (CODE_TOP + CODE_BOTTOM) / 2, 0])
        title = label("THE ONLY DIFFERENCE", 14, TEXT_MUTED, weight=NORMAL).move_to(box.get_corner(UL) + np.array([0.25, -0.22, 0]),
                                                                                aligned_edge=LEFT)
        code.move_to(box.get_corner(UL) + np.array([0.15, -0.42, 0]), aligned_edge=UL)
        self.code = code
        self.cbar = Rectangle(width=box.width - 0.2, height=abs(code.code_lines[0].get_y() - code.code_lines[1].get_y()),
                              fill_color=BFS_C, fill_opacity=0, stroke_width=0).move_to([0, code.code_lines[POP_LINE].get_y(), 0])
        self.note = self.pop_note("BFS")
        return VGroup(box, title, self.cbar, code)

    def pop_note(self, name):
        """The tag after the pop line: which search it is, and the swap that makes the other one."""
        color, other = (BFS_C, "pop() for DFS") if name == "BFS" else (DFS_C, "popleft() for BFS")
        chip = label(name, 16, color)
        rest = label(f"·  {other}", 16, TEXT_MUTED, weight=NORMAL)
        note = VGroup(chip, rest).arrange(RIGHT, buff=0.15)
        return note.next_to(self.code.code_lines[POP_LINE], RIGHT, buff=0.4)

    # ---------------------------------------------------------------- timeline
    def construct(self):
        if any(not (SFX / f"{name}.wav").exists() for name in SFX_NAMES):
            make_sfx()
        if any(not (SFX / f"{name}.wav").exists() for name in BD_SFX):
            make_bfs_sfx()
        if self.music and not TRACK.exists():
            make_track(TRACK)
        self.camera.background_color = "#0D0F22"
        self.stage()
        self.b = 0
        self.cap, self.cap_since, self.head = VGroup(), None, VGroup()
        self.race = ValueTracker(0)
        self.routes = {"BFS": ValueTracker(0), "DFS": ValueTracker(0)}
        self.dim = ValueTracker(1.0)
        self.sound = Sonifier(LENGTH * BEAT)
        if self.music:
            self.add_sound(str(TRACK))

        self.first_frame()
        self.chapter("intro", "Same map, two searches")
        self.moment("hook")   # both maps, the pins, the code and the question are all up on the first frame
        self.moment("topic")  # BFS VS DFS is the title on the first frame
        self.tick(beats=2)
        self.sound.put(bell(scale_hz(7), 0.6), self.b * BEAT, -0.5, 0.25)  # the start and goal pins ping
        self.sound.put(bell(scale_hz(11), 0.6), (self.b + 0.5) * BEAT, 0.5, 0.25)
        self.tick(self.ring(self.panels[0].marks), self.ring(self.panels[1].marks), beats=2)
        self.difference()
        self.chapter("race", "The race")
        self.race_on()
        self.chapter("routes", "The routes")
        self.show_routes()
        self.chapter("why", "Queue vs stack")
        self.why()
        self.chapter("outro", "Takeaway")
        self.takeaway()
        self.rewind()
        assert self.b == LENGTH, f"{self.b} beats, the loop needs {LENGTH}"
        self.close_caption()
        self.renderer.file_writer.add_audio_segment(self.sound.segment(), 0)

    def ring(self, mob, color=WHITE):
        ring = SurroundingRectangle(mob, buff=0.05, corner_radius=0.06, stroke_color=color, stroke_width=3)
        return ring.animate(remover=True, rate_func=rate_functions.ease_out_cubic).scale(1.15).set_stroke(opacity=0)

    def first_frame(self):
        """Everything on screen at 0s (also the loop's last frame)."""
        title = label("B F S   V S   D F S", 20, TEXT_MUTED, weight=NORMAL).move_to([0, TITLE_Y, 0])
        n = len(self.city.pos)
        stats = VGroup(label(f"{n:,} INTERSECTIONS", 17, TEXT_MUTED, weight=NORMAL), Dot(radius=0.04, color=ACCENT),
                       label("SAME START, SAME GOAL", 17, TEXT_LIGHT)).arrange(RIGHT, buff=0.15).move_to([0, STATS_Y, 0])
        rules = VGroup(*[Line([x - 0.9, STATS_Y - 0.25, 0], [x + 0.9, STATS_Y - 0.25, 0], stroke_color=PANEL_EDGE, stroke_width=2)
                         for x in (-2.7, -0.9, 0.9, 2.7)])
        self.panels = [self.make_panel("BFS", MAP_X[0]), self.make_panel("DFS", MAP_X[1])]
        self.code_box = self.code_panel()
        bar = RoundedRectangle(width=7.65, height=0.62, corner_radius=0.1, fill_color=PANEL_BG, fill_opacity=1,
                               stroke_color=PANEL_EDGE, stroke_width=2).move_to([0, CAPTION_Y, 0])
        credit = VGroup(label("Golden Gate Bridge → Oracle Park, San Francisco. DFS takes neighbours in OSM id order.",
                              11, TEXT_MUTED, weight=NORMAL),
                        label("Road network © OpenStreetMap contributors (ODbL)", 11, TEXT_MUTED, weight=NORMAL))
        credit.arrange(DOWN, buff=0.06).move_to([0, NOTE_Y, 0]).set_opacity(0.7)
        self.add(title, stats, rules, *self.panels, self.code_box, self.note, bar, credit)
        self.headline("Which search finds the better route?", {"better route?": ACCENT})
        self.add(self.head)
        self.caption("Golden Gate → Oracle Park.", {"Golden Gate": ACCENT, "Oracle Park.": "#4CD97B"})
        self.add(self.cap)
        self.bit = Bit().scale(0.4)
        self.bit.brows.become(self.bit.make_brows("raised"))
        self.add(self.stand(self.bit, [3.25, CODE_BOTTOM + 0.12, 0]))
        for panel in self.panels:
            self.live(panel, lambda dt, panel=panel: self.refresh_panel(panel))

    def difference(self):
        """The code: one line, two searches."""
        self.moment("reveal")
        self.sfx("bd_pin", gain=-4)
        self.tick(self.cbar.animate(rate_func=snap).set_fill(opacity=0.22), Indicate(self.note, color=BFS_C, scale_factor=1.15),
                  *self.caption("One line apart: popleft() vs pop().", {"popleft()": BFS_C, "pop().": DFS_C}),
                  *self.headline("Same loop. One line apart."), beats=2)
        self.tick(Indicate(self.code.code_lines[POP_LINE], color=DFS_C, scale_factor=1.06), beats=2)

    def race_on(self):
        """Both searches run at the same pace, from the drop; the faster one to the goal lights up first."""
        bfs, dfs = self.runs["BFS"]["checked"], self.runs["DFS"]["checked"]
        beats = BREAK - DROP
        pace = max(bfs, dfs) / beats  # intersections a beat: the slower search reaches the goal on the break
        first, second = ("DFS", "BFS") if dfs < bfs else ("BFS", "DFS")
        first_at = DROP + self.runs[first]["checked"] / pace
        self.sonify_race(pace)
        lines = {DROP: ("BFS spreads in rings...", {"BFS": BFS_C}),
                 DROP + 4: ("...DFS dives down one road.", {"DFS": DFS_C}),
                 DROP + 8: ("Same pace. Who's first?", {"first?": ACCENT})}
        for b in range(DROP, BREAK):
            anims = [self.race.animate(rate_func=linear).set_value((b + 1 - DROP) * pace)]
            if b in lines and b != int(first_at) + 1:
                anims += self.caption(*lines[b])
            if b == DROP:
                anims += self.headline("Go!", {"Go!": ACCENT})
            if b <= first_at < b + 1:
                self.sfx(f"bd_found_{first.lower()}", offset=(first_at - b) * BEAT)
            if b == int(first_at) + 1:
                self.moment("twist")
                anims += self.caption(f"{first} reaches Oracle Park FIRST!", {first: BFS_C if first == "BFS" else DFS_C})
                anims += self.headline(f"{first} checked {abs(bfs - dfs):,} fewer.")
                anims.append(self.ring(self.panels[1 if first == "DFS" else 0].bar, DFS_C if first == "DFS" else BFS_C))
            self.tick(*anims)
        self.sfx(f"bd_found_{second.lower()}")

    def sonify_race(self, pace):
        """Both searches play from the drop, 30 notes a second each: BFS (left, bells) climbs the scale ring by
        ring; DFS (right, plucks) rises and falls with its distance to the goal. Each ends on a chord as it arrives."""
        t0 = DROP * BEAT
        for name, voice, pan, gain in (("BFS", bell, -0.6, 0.22), ("DFS", pluck, 0.6, 0.2)):
            pitch = self.runs[name]["pitch"]
            end = t0 + len(pitch) / pace * BEAT
            for j, t in enumerate(np.arange(t0, end, 1 / 30)):
                k = pitch[min(int((t - t0) / BEAT * pace), len(pitch) - 1)]
                self.sound.put(voice(scale_hz(round(k))), t, pan, gain)
                if name == "BFS" and j % 3 == 0:  # a sparkle an octave up
                    self.sound.put(bell(scale_hz(round(k) + 5), 0.1), t + 1 / 60, pan, gain * 0.35)
            self.sound.chord(voice, (TOP - 4, TOP - 2, TOP, TOP + 2), end, pan, gain * 1.4)

    def show_routes(self):
        """The routes: BFS's short one, then DFS's... all of it, with its odometer."""
        bfs, dfs = self.runs["BFS"], self.runs["DFS"]
        self.moment("payoff")
        self.sfx("whoosh", gain=-4)
        # Each map's footer note turns into its route's odometer.
        bfs_note, dfs_note = (panel.note for panel in self.panels)
        # BFS's route: a run up the scale as it draws, landing on a chord.
        t0, dur = self.b * BEAT, 2 * BEAT
        for t in np.arange(0, dur, 1 / 24):
            self.sound.put(bell(scale_hz(round(TOP * smooth(t / dur)))), t0 + t, -0.5, 0.22)
        self.sound.chord(bell, (TOP - 6, TOP - 4, TOP - 2, TOP), t0 + dur - BEAT / 4, -0.3, 0.3)
        self.tick(self.routes["BFS"].animate(rate_func=smooth).set_value(len(bfs["route"])), self.dim.animate.set_value(0.3),
                  UpdateFromAlphaFunc(bfs_note, self.odometer(bfs_note, bfs["miles"], BFS_C)),
                  *self.caption(f"BFS: {bfs['miles']:.1f} mi.", {"BFS:": BFS_C}),
                  *self.headline("Show me the route."), beats=2)

        # DFS's route, four beats long, the odometer running up: a scramble of notes that follows the road
        # east and west across the stereo field.
        self.sfx("slide_down", gain=-8)
        for k in range(16):
            self.sfx("bd_tick", offset=k * BEAT / 4, gain=-12)
        route, t0, dur = dfs["route"], self.b * BEAT, 4 * BEAT
        for t in np.arange(0, dur, 1 / 30):
            node = route[min(int(len(route) * t / dur), len(route) - 1)]
            self.sound.put(pluck(scale_hz(round(TOP * self.closeness(node)))), t0 + t, self.pan_of(node), 0.2)
        self.tick(self.routes["DFS"].animate(rate_func=linear).set_value(len(dfs["route"])),
                  UpdateFromAlphaFunc(dfs_note, self.odometer(dfs_note, dfs["miles"], DFS_C, rate=linear)),
                  *self.caption("DFS's route... still going...", {"DFS's": DFS_C}),
                  self.bit.look(UP), beats=4, bit_free=False)
        self.moment("surprise")
        self.sfx("bd_wah", gain=-5)
        self.moment("joke")
        self.tick(*self.caption(f"{dfs['miles']:.0f} MILES?!", {f"{dfs['miles']:.0f} MILES?!": DFS_C}),
                  *self.headline("DFS took the SCENIC route.", {"SCENIC": DFS_C}),
                  self.ring(dfs_note, DFS_C), self.bit.express("open", "worried"), self.bit.look(ORIGIN), beats=2, bit_free=False)

    def odometer(self, note, miles, color, rate=smooth):
        """Run a map's footer note up to its route's length."""
        corner = note.get_left()

        def run(m, alpha):
            text = f"route {miles * rate(alpha):.1f} mi"
            if text != getattr(m, "text_now", None):
                m.become(label(text, 20, color).move_to(corner, aligned_edge=LEFT))
                m.text_now = text
        return run

    def why(self):
        """Why: a queue takes the oldest (rings), a stack the newest (one long dive)."""
        self.sound.chord(bell, (5, 7, 9, 12), self.b * BEAT, -0.5, 0.25)  # each search keeps its voice: the queue rings
        self.tick(self.bit.express("smile", "raised"), self.cbar.animate(rate_func=snap).set_fill(BFS_C, 0.25), Indicate(self.code.code_lines[POP_LINE], color=BFS_C),
                  *self.caption("popleft(): oldest first = rings.", {"popleft():": BFS_C}),
                  *self.headline("Queue vs stack. That's it.", {"Queue": BFS_C, "stack.": DFS_C}), beats=4)
        dfs_code = Code(code_string=CODE.replace("popleft()", "pop()"), language="python", formatter_style="one-dark",
                        background="rectangle", add_line_numbers=True, paragraph_config={"font": MONO})
        dfs_code.scale(self.code.code_lines[0].height / dfs_code.code_lines[0].height)
        new_line = dfs_code.code_lines[POP_LINE].move_to(self.code.code_lines[POP_LINE], aligned_edge=LEFT)
        self.old_line, self.old_note = self.code.code_lines[POP_LINE].copy(), self.note
        new_note = self.pop_note("DFS")
        self.sfx("bd_pin", gain=-4)
        self.sound.chord(pluck, (12, 9, 7, 4), self.b * BEAT, 0.5, 0.25)  # ...and the stack plucks, diving down
        self.tick(Transform(self.code.code_lines[POP_LINE], new_line, rate_func=snap), Transform(self.note, new_note, rate_func=snap),
                  self.cbar.animate(rate_func=snap).set_fill(DFS_C, 0.25),
                  *self.caption("pop(): newest first = dives.", {"pop():": DFS_C}),
                  *self.headline("BFS: fewest stops. DFS: any path.", {"BFS:": BFS_C, "DFS:": DFS_C}), beats=4)

    def takeaway(self):
        self.moment("cta")
        button = self.subscribe_button().scale(0.62).move_to([0, -1.72, 0])
        self.sfx("pop")
        self.tick(FadeOut(self.code_box, rate_func=snap), FadeOut(self.note, rate_func=snap),
                  FadeIn(button, shift=UP * 0.3, rate_func=snap), *self.caption("Real miles? That's Dijkstra.", {"Dijkstra.": ACCENT}),
                  *self.headline(f"Shortest drive: {self.best_miles:.1f} mi.", {f"{self.best_miles:.1f} mi.": ACCENT}),
                  self.bit.look(LEFT), beats=2)
        self.tick(self.pulse(button, times=1), beats=2)
        done, check = self.subscribe_button(subscribed=True)
        Group(done, check).scale(0.62).move_to(button)
        self.done = VGroup(done[1], check)
        self.sfx("pop")
        self.sfx("ding", offset=0.1)
        self.tick(Transform(button[0], done[0], rate_func=snap), button[1].animate(rate_func=snap).set_opacity(0),
                  FadeIn(done[1], scale=1.2, rate_func=snap), Create(check, rate_func=snap), self.confetti(button),
                  *self.caption("Subscribe for more!"), *self.headline("Queue spreads. Stack dives.", {"Queue": BFS_C, "Stack": DFS_C}),
                  self.bit.arms_up(), self.bit.express("grin", "raised"), self.bit.look(ORIGIN), beats=2.5, bit_free=False)
        self.tick(self.bit.arms_rest(), self.bit.express("smile", "raised"), beats=0.5, bit_free=False)
        self.button = button

    def rewind(self):
        """The loop: the maps wipe back to bare streets, and the code and lines return as on the first frame."""
        self.moment("loop")
        self.sfx("whoosh", gain=-2)
        for i, k in enumerate(range(TOP, 3, -1)):  # a quick run back down the scale
            self.sound.put(bell(scale_hz(k), 0.2), (self.b + i / (TOP - 3)) * BEAT * 0.9, 0.0, 0.18)
        self.code.code_lines[POP_LINE].become(self.old_line)
        self.cbar.set_fill(BFS_C, 0)
        anims = [FadeOut(m, rate_func=snap) for m in (self.button, self.done)]
        for panel, text in zip(self.panels, ("spreads in rings", "dives down one road")):
            corner = panel.note.get_left()
            panel.note.become(label(text, 13, TEXT_MUTED, weight=NORMAL).move_to(corner, aligned_edge=LEFT))
            panel.note.text_now = None
        anims += [FadeIn(self.code_box, rate_func=snap)]
        self.remove(self.note)
        self.note = self.pop_note("BFS")
        anims += [FadeIn(self.note, rate_func=snap)]
        anims += [self.race.animate(rate_func=snap).set_value(0), self.dim.animate(rate_func=snap).set_value(1)]
        anims += [self.routes[n].animate(rate_func=snap).set_value(0) for n in self.routes]
        anims += self.caption("Golden Gate → Oracle Park.", {"Golden Gate": ACCENT, "Oracle Park.": "#4CD97B"})
        self.cap_since = None  # the replay carries this line on: it was logged once, from 0s
        anims += self.headline("Which search finds the better route?", {"better route?": ACCENT})
        self.tick(*anims, bit_free=False)


class Thumbnail(ThumbnailMixin, BfsDfs):
    def design(self):
        """Shorts/Reels cover: BFS VS DFS over the two finished maps, the DFS route scribbled across the city."""
        self.race, self.dim = ValueTracker(10 ** 6), ValueTracker(0.35)
        self.routes = {"BFS": ValueTracker(10 ** 6), "DFS": ValueTracker(10 ** 6)}
        maps = Group()
        for name, x in (("BFS", -1.95), ("DFS", 1.95)):
            panel = self.make_panel(name, x)
            self.refresh_panel(panel)
            maps.add(Group(panel.picture, panel[1], panel[5]))
        maps.move_to(DOWN * 1.0)
        words = VGroup(headline_text("BFS", 150, BFS_C), headline_text("vs", 80, TEXT_LIGHT), headline_text("DFS", 150, DFS_C))
        words.arrange(RIGHT, buff=0.3).scale_to_fit_width(7.0).move_to(UP * 4.6)
        sub = headline_text(f"{self.runs['BFS']['miles']:.1f} mi vs {self.runs['DFS']['miles']:.0f} mi", 60, ACCENT)
        sub.scale_to_fit_width(6.4).next_to(words, DOWN, buff=0.3)
        self.add(maps, words, sub)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "build":
    build_map(sys.argv[2])
