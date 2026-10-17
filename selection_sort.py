"""Selection sort: find the smallest, swap it to the front, repeat.

The title itself gets selection-sorted into place. Then six bars are sorted pass by pass with a
comparison counter, the code is walked through (16:9), and the cost: n(n-1)/2 comparisons.

Render:  .venv/bin/manim -qh --fps 30 selection_sort.py SelectionSort
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 selection_sort.py SelectionSort
Thumbnail: .venv/bin/manim -s -r 1280,720 selection_sort.py Thumbnail
"""

from bitbybit import *

VALUES = [29, 10, 14, 37, 13, 5]
CODE = """def selection_sort(a):
    for i in range(len(a)):
        low = i
        for j in range(i + 1, len(a)):
            if a[j] < a[low]:
                low = j
        a[i], a[low] = a[low], a[i]"""
SORTED_GREEN = "#43A047"

BAR_W, BAR_GAP, BAR_UNIT = 0.8, pick(0.25, 0.3), 0.09  # BAR_UNIT: height per value
BARS_X, BARS_BASE = pick(3.75, 0.0), pick(-1.7, -0.7)
COUNTER_AT = pick([3.75, 2.6, 0], [0, 3.5, 0])
BIT_AT = pick([-4.6, -2.6, 0], [-2.4, -4.7, 0])


class SelectionSort(BitScene):
    code_width = 7.0

    # ---------------------------------------------------------------- pieces
    def line(self, bit, text, **kwargs):
        """Bit's lines: above him on 16:9; up and to the right on 9:16, below the bars."""
        return self.say(bit, text, pick(UP, UR), **kwargs)

    def slot_x(self, k):
        return BARS_X + (k - (len(VALUES) - 1) / 2) * (BAR_W + BAR_GAP)

    def bar(self, value, k):
        rect = RoundedRectangle(width=BAR_W, height=value * BAR_UNIT, corner_radius=0.08, fill_color="#5C6BC0",
                                fill_opacity=1, stroke_color=INK, stroke_width=3)
        rect.move_to([self.slot_x(k), BARS_BASE, 0], aligned_edge=DOWN)
        label = Text(str(value), font=MONO, weight=BOLD, font_size=28, color=TEXT_LIGHT).next_to(rect, UP, buff=0.1)
        return VGroup(rect, label)

    def bars(self, values=VALUES):
        return [self.bar(v, k) for k, v in enumerate(values)]

    def paint(self, bar, color):
        return bar[0].animate.set_fill(color)

    def scan_arrow(self, k):
        return Arrow([self.slot_x(k), BARS_BASE - 0.85, 0], [self.slot_x(k), BARS_BASE - 0.12, 0], color=ACCENT,
                     buff=0, stroke_width=7, max_tip_length_to_length_ratio=0.35)

    def counter(self, n):
        return Text(f"comparisons: {n}", font=MONO, weight=BOLD, font_size=30, color=TEXT_LIGHT).move_to(COUNTER_AT)

    def swap(self, bars, i, j):
        """Swap the bars at positions i and j along arcs; returns the new list."""
        if i != j:
            self.sfx("whoosh", gain=-4)
            a, b = bars[i], bars[j]
            self.play(a.animate(path_arc=-PI / 2).shift(RIGHT * (self.slot_x(j) - self.slot_x(i))),
                      b.animate(path_arc=-PI / 2).shift(LEFT * (self.slot_x(j) - self.slot_x(i))), run_time=0.5)
            bars[i], bars[j] = b, a
        return bars

    def hook_visual(self):
        """The bars with the smallest one picked out and an arrow sending it to the front."""
        bars = self.bars()
        bars[5][0].set_fill(ACCENT)
        arc = CurvedArrow(bars[5][1].get_top() + UP * 0.15, bars[0][1].get_top() + UP * 0.15, angle=PI / 3,
                          color=ACCENT, stroke_width=7)
        bit = Bit().scale(0.95).move_to([0, -3.6, 0])
        bit.brows.become(bit.make_brows("raised"))
        bit.mouth.become(bit.make_mouth("open"))
        glow = Circle(radius=3.4, fill_color=ACCENT, fill_opacity=0.12, stroke_width=0).move_to([0, 0.6, 0])
        return Group(glow, VGroup(*bars), arc, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "Find the smallest, swap, repeat")
            self.hook_open(("Find the smallest. Swap.", "Repeat. That's it?!"),
                           "Find the smallest. Swap. Repeat. That's it?", sound="pop", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.sorted_title()
        self.chapter("idea", "The idea: pick the smallest")
        bit, bars = self.idea(bit, title)
        self.chapter("passes", "Step by step")
        bars = self.passes(bit, bars)
        if not SHORT:
            self.chapter("code", "The code, line by line")
            self.code_walk(bit)
        self.chapter("cost", "How fast is it? O(n²)")
        self.cost(bit, bars)
        self.chapter("joke", "The selection sort joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["Find the smallest. Swap. Repeat."], ["Find the smallest.", "Swap. Repeat."]),
                    "Select the subscribe button.\nSmallest effort ever!",
                    loop_line="So... is that REALLY\nall sorting is?", loop_finale=self.hook_look)

    def sorted_title(self):
        """The opening: the title's letters arrive shuffled and get selection-sorted into place."""
        words = pick(["SELECTION SORT"], ["SELECTION", "SORT"])
        size = pick(0.82, 0.78)
        rows = []
        for r, word in enumerate(words):
            tiles = VGroup()
            for ch in word:
                box = RoundedRectangle(width=size, height=size * 1.15, corner_radius=0.1, fill_color="#2C3166",
                                       fill_opacity=1, stroke_color="#6A70C0", stroke_width=3)
                letter = Text(ch, font=FONT, weight=BOLD, font_size=44, color=HEADLINE) if ch != " " else VMobject()
                tiles.add(VGroup(box, letter.move_to(box)) if ch != " " else VGroup(box.set_opacity(0)))
            tiles.arrange(RIGHT, buff=0.06).move_to(UP * pick(2.2, 3.4 - 1.1 * r))
            rows.append(tiles)
        homes = [[t.get_center() for t in row] for row in rows]
        # A fixed shuffle: tile k of each row starts at position order[p].
        orders = [list(np.random.default_rng(5 + r).permutation(len(row))) for r, row in enumerate(rows)]
        for row, order, home in zip(rows, orders, homes):
            for pos, k in enumerate(order):
                row[k].move_to(home[pos])

        bit = Bit().move_to(DOWN * 1.7)
        self.sfx("boing")
        self.play(FadeIn(bit, shift=UP * 2.0), run_time=0.5, rate_func=rate_functions.ease_out_back)
        self.sfx("pop")
        self.play(*[LaggedStart(*[FadeIn(t, scale=0.6) for t in row], lag_ratio=0.05) for row in rows],
                  bit.look(UP), run_time=0.6)
        # Selection sort on the tiles: for each position, pick the tile that belongs there and swap it in.
        for row, order, home in zip(rows, orders, homes):
            for i in range(len(order)):
                j = order.index(i)
                if j == i:
                    continue
                a, b = row[order[i]], row[i]
                self.sfx("pop", gain=-6)
                self.play(b.animate(path_arc=-PI / 2).move_to(home[i]), a.animate(path_arc=-PI / 2).move_to(home[j]),
                          run_time=0.16)
                order[i], order[j] = order[j], order[i]
        title = VGroup(*rows)
        self.sfx("ding")
        self.play(title.animate(rate_func=there_and_back).scale(1.06), bit.look(ORIGIN), bit.express("grin", "smug"),
                  run_time=0.35)
        self.moment("topic")
        spoken = self.voice("Selection sort.", captioned=True)
        self.play(bit.talk(max(spoken, 0.5)))
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        return bit, title

    def idea(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: sort ANY list with one\nsimple idea. Step by step.", UR, gesture=bit.point(0, 165))
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.6).move_to(BIT_AT), run_time=0.4)
        bars = self.bars()
        self.sfx("pop")
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.12), run_time=0.8)
        self.line(bit, "The idea: find the SMALLEST,\nput it first. Then repeat.")
        return bit, bars

    def scan(self, bars, i, count, narrate):
        """One pass: scan positions i.. for the smallest bar; returns (its position, new count)."""
        low, values = i, self.values
        self.play(self.paint(bars[i], ACCENT), run_time=0.2)
        arrow = self.scan_arrow(i)
        self.play(GrowArrow(arrow), run_time=0.15)
        if narrate:
            self.line(self.bit, f"{values[i]} is the smallest...\nso far.", speech=f"{values[i]} is the smallest. So far.")
        for j in range(i + 1, len(bars)):
            count += 1
            self.sfx("blip", gain=-6)
            self.play(arrow.animate.become(self.scan_arrow(j)), self.counter_text.animate.become(self.counter(count)),
                      run_time=0.2 if narrate else 0.14)
            if values[j] < values[low]:
                self.sfx("pop")
                self.play(self.paint(bars[low], "#5C6BC0"), self.paint(bars[j], ACCENT), run_time=0.2)
                if narrate and low == i:  # explain the rule once
                    self.line(self.bit, f"{values[j]} is smaller!\nNew smallest.", speech=f"{values[j]} is smaller! New smallest.")
                low = j
        self.play(FadeOut(arrow), run_time=0.15)
        return low, count

    def passes(self, bit, bars):
        self.values = list(VALUES)
        self.bit = bit
        self.counter_text = self.counter(0)
        self.play(FadeIn(self.counter_text), run_time=0.2)
        count = 0
        for i in range(len(bars) - 1):
            narrate = i == 0 and not SHORT
            if i == 0 and SHORT:
                self.line(bit, "Scan for the SMALLEST...")
            if i == 1:
                self.line(bit, "Green is done. Now find the\nsmallest of the REST.")
            low, count = self.scan(bars, i, count, narrate)
            if i == 0:
                self.line(bit, "5 is the smallest of all.\nSwap it to the front!",
                          speech="Five is the smallest of all. Swap it to the front!")
            if low == i and i == 1 and not SHORT:
                self.line(bit, "10 is already in place.\nNo swap needed!", speech="Ten is already in place. No swap needed!")
            bars = self.swap(bars, i, low)
            self.values[i], self.values[low] = self.values[low], self.values[i]
            if i == 0:
                self.moment("reveal")  # the first spot is final
            self.sfx("ding" if i == 0 else "pop", gain=None if i == 0 else -4)
            self.play(self.paint(bars[i], SORTED_GREEN), run_time=0.2)
        self.play(self.paint(bars[-1], SORTED_GREEN), run_time=0.2)
        self.moment("payoff")
        self.sfx("ding")
        self.play(*[b.animate(rate_func=there_and_back).shift(UP * 0.25) for b in bars],
                  bit.express("grin", "raised"), bit.arms_up(run_time=0.3), run_time=0.45)
        self.line(bit, "Sorted! 6 items took\n15 comparisons.", speech="Sorted! Six items took fifteen comparisons.")
        self.play(bit.arms_rest(run_time=0.3), bit.express("smile", "neutral"), run_time=0.3)
        return bars

    def code_walk(self, bit):
        code = self.make_code(CODE).to_corner(UL, buff=0.5).shift(DOWN * 0.35)
        panel = VGroup(self.shadow(code.background), code)
        self.sfx("whoosh", gain=-4)
        self.play(FadeIn(panel, shift=RIGHT * 0.5), run_time=0.5)
        self.moment("twist")
        bar = self.line_bar(code, 1)
        self.play(FadeIn(bar), run_time=0.2)
        self.line(bit, "Outer loop: which spot\nare we filling?", gesture=bit.point(0, 150))
        self.play(bit.arms_rest(run_time=0.2), run_time=0.2)
        self.play(bar.animate.stretch_to_fit_height(abs(code.code_lines[2].get_y() - code.code_lines[5].get_y()) + bar.height)
                  .set_y((code.code_lines[2].get_y() + code.code_lines[5].get_y()) / 2), run_time=0.3)
        self.line(bit, "Inner loop: find the smallest\nin the rest. Remember where.")
        self.play(bar.animate.stretch_to_fit_height(self.line_bar(code, 6).height).set_y(code.code_lines[6].get_y()),
                  run_time=0.3)
        self.line(bit, "Then ONE swap. Python swaps\ntwo values in a single line!")
        self.sfx("whoosh")
        self.play(FadeOut(panel), FadeOut(bar), run_time=0.4)

    def cost(self, bit, bars):
        self.sfx("whoosh")
        self.play(*[FadeOut(b) for b in bars], FadeOut(self.counter_text), run_time=0.4)
        rows = [("6 items", "15"), ("1,000 items", "499,500"), ("1,000,000 items", "499,999,500,000")]
        table = VGroup(*[
            VGroup(Text(n, font=FONT, weight=BOLD, font_size=34, color=TEXT_LIGHT),
                   Text(c, font=MONO, weight=BOLD, font_size=34, color=ACCENT)).arrange(DOWN if VERTICAL else RIGHT,
                                                                                         buff=pick(0.5, 0.12))
            for n, c in rows
        ]).arrange(DOWN, buff=pick(0.35, 0.45), aligned_edge=LEFT).move_to(pick([2.9, 1.0, 0], [0, 1.8, 0]))
        head = Text("comparisons", font=FONT, font_size=28, color=TEXT_MUTED).next_to(table, UP, buff=0.35)
        self.play(FadeIn(head), FadeIn(table[0], shift=UP * 0.2), run_time=0.4)
        if not SHORT:
            self.line(bit, "Every pass compares the rest.\nThat adds up FAST.")
        self.sfx("pop")
        self.play(FadeIn(table[1], shift=UP * 0.2), run_time=0.3)
        self.moment("surprise")
        self.sfx("boing")
        self.play(FadeIn(table[2], scale=1.4), bit.express("open", "worried"), run_time=0.4)
        self.play(Indicate(table[2][1], color="#FF6B6B", scale_factor=1.15), run_time=0.5)
        self.line(bit, "A million items: 500 BILLION\ncomparisons. Ouch!", speech="A million items: five hundred billion comparisons. Ouch!")
        if not SHORT:
            self.line(bit, "That's about n squared over 2:\nwe call it O(n²).", speech="That's about n squared over two. We call it big O of n squared.")
            self.line(bit, "Great for small lists. And it\nonly swaps n times!")
            self.line(bit, "For big lists, Python's\nsorted() is MUCH faster.", speech="For big lists, Python's sorted function is much faster.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "Why is the smallest number\nalways so confident?", "It knows it'll be\nSELECTED first.",
                  speech_punch="It knows it'll be selected first.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, SelectionSort):
    def design(self):
        """PICK. SWAP. REPEAT.: the bars half sorted, the smallest jumping to the front."""
        values = [5, 10, 37, 14, 13, 29]
        bars = VGroup()
        for k, v in enumerate(values):
            rect = RoundedRectangle(width=0.95, height=v * 0.11, corner_radius=0.1, stroke_color=INK, stroke_width=4,
                                    fill_opacity=1, fill_color=SORTED_GREEN if k < 2 else (ACCENT if v == 13 else "#5C6BC0"))
            bars.add(rect.move_to([0.0 + k * 1.15, -3.2, 0], aligned_edge=DOWN))
        arc = CurvedArrow(bars[4].get_top() + UP * 0.2, bars[2].get_top() + UP * 0.2, angle=PI / 2.5, color=ACCENT,
                          stroke_width=12)
        words = VGroup(headline_text("PICK.", 130, ACCENT), headline_text("SWAP.", 130, TEXT_LIGHT),
                       headline_text("REPEAT.", 130, HEADLINE)).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        words.to_corner(UL, buff=0.5)
        bit = Bit().scale(0.9).move_to([5.6, 2.3, 0])
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("smug"))
        self.add(bars, arc, words, bit)
