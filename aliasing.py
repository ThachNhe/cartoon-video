"""Aliasing: `b = a` gives a list a second name; it does not copy it.

Name tags point at list boxes: after `b = a` both tags point at the same box, so `b.append(4)`
shows up in `a`. With `b = a.copy()` b gets its own box and `a` stays untouched.

Render:  .venv/bin/manim -qh --fps 30 aliasing.py Aliasing
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 aliasing.py Aliasing
Thumbnail: .venv/bin/manim -s -r 1280,720 aliasing.py Thumbnail
"""

from bitbybit import *

SHARED = """a = [1, 2, 3]
b = a
b.append(4)
print(a)"""
COPIED = SHARED.replace("b = a", "b = a.copy()")
TAG_A, TAG_B = "#80DEEA", "#FFAB91"

# Where things go: name tags, the list boxes they point at, and Bit.
TAG_X, BOX_X = pick(1.0, -2.8), pick(2.4, -1.6)  # BOX_X is the boxes' left edge
ROW_A, ROW_B = pick(2.0, -0.55), pick(0.4, -1.8)  # 9:16: below the code and its output
BIT_AT = pick([2.6, -2.8, 0], [-2.3, -5.0, 0])


class Aliasing(BitScene):
    code_width = pick(5.6, 6.0)

    # ---------------------------------------------------------------- pieces
    def name_tag(self, name, color, y):
        box = RoundedRectangle(width=0.95, height=0.75, corner_radius=0.16, fill_color=color, fill_opacity=1,
                               stroke_color=INK, stroke_width=4)
        tag = VGroup(box, Text(name, font=MONO, weight=BOLD, font_size=42, color=INK).move_to(box))
        return tag.move_to([TAG_X, y, 0])

    def cell(self, value):
        square = Square(0.72, fill_color="#2C3166", fill_opacity=1, stroke_color="#6A70C0", stroke_width=4)
        return VGroup(square, Text(str(value), font=MONO, weight=BOLD, font_size=34, color=TEXT_LIGHT).move_to(square))

    def list_box(self, values, y):
        cells = VGroup(*[self.cell(v) for v in values]).arrange(RIGHT, buff=0)
        return cells.move_to([BOX_X, y, 0], aligned_edge=LEFT)

    def link(self, tag, box, color):
        return Arrow(tag.get_right(), box.get_left(), color=color, buff=0.12, stroke_width=7,
                     max_tip_length_to_length_ratio=0.25)

    def line(self, bit, text, **kwargs):
        """Bit's lines: above him on 16:9; up and to the right on 9:16, so the bubble stays below the diagram."""
        return self.say(bit, text, pick(UP, UR), **kwargs)

    def append_cell(self, box, value):
        """Grow `box` by one cell; returns the animation."""
        cell = self.cell(value).next_to(box, RIGHT, buff=0)
        box.add(cell)
        return FadeIn(cell, shift=LEFT * 0.4, scale=1.3)

    def hook_visual(self):
        """The surprise: print(a) shows a 4 nobody put there."""
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0.22)
        console = self.console(7.2, 2.6).move_to(UP * 0.9)
        prompt = Text(">>> print(a)", font=MONO, font_size=40, color=TEXT_MUTED)
        result = Text("[1, 2, 3, 4]", font=MONO, weight=BOLD, font_size=56, color=CONSOLE_GREEN)
        VGroup(prompt, result).arrange(DOWN, aligned_edge=LEFT, buff=0.2).next_to(console[2], DOWN, buff=0.2,
                                                                                  aligned_edge=LEFT)
        ring = Circle(radius=0.5, stroke_color="#FF4D4D", stroke_width=9).move_to(result[-2])
        bit = self.shocked_bit(1.3).move_to(DOWN * 3.0)
        return Group(glow, console, prompt, result, ring, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "Why did my list change?")
            self.hook_open(("Why did my list change", "BY ITSELF?!"), "Why did my list change by itself?",
                           sound="oops", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.title_intro("ALIASING", "Aliasing.")
        self.chapter("bug", "b = a does not copy")
        bit = self.bug(bit, title)
        self.chapter("why", "Two names, one list")
        self.why(bit)
        self.chapter("fix", "The fix: .copy()")
        self.fix(bit)
        self.chapter("joke", "The aliasing joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["= shares, .copy() copies."], ["= shares,", ".copy() copies."]),
                    "Share this video.\nOr .copy() the link!",
                    loop_line="So why did a change\nall by itself?", loop_finale=self.hook_look)

    def bug(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: why your list changes\nwhen you didn't touch it.", UR, gesture=bit.point(0, 165))
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.6).move_to(BIT_AT), run_time=0.4)

        code = self.make_code(SHARED)
        if VERTICAL:
            code.to_edge(UP, buff=1.7).set_x(0)
        else:
            code.to_corner(UL, buff=0.5).shift(DOWN * 0.35)
        console = self.console(pick(3.8, 3.6), 1.1).next_to(code, DOWN, buff=0.3, aligned_edge=LEFT)
        self.sfx("whoosh", gain=-4)
        self.play(FadeIn(VGroup(self.shadow(code.background), code), shift=RIGHT * 0.5), FadeIn(console), run_time=0.6)
        self.code, self.console_box = code, console

        bar = self.line_bar(code, 0)
        tag_a, box = self.name_tag("a", TAG_A, ROW_A), self.list_box([1, 2, 3], ROW_A)
        arrow_a = self.link(tag_a, box, TAG_A)
        self.sfx("pop")
        self.play(FadeIn(bar), FadeIn(tag_a, scale=1.3), FadeIn(box, shift=LEFT * 0.3), bit.look(pick(UL, UP)), run_time=0.4)
        self.play(GrowArrow(arrow_a), run_time=0.3)
        self.line(bit, "a is a list:\n1, 2, 3.", speech="a is a list: one, two, three.")

        self.bar_to(bar, code, 1)
        tag_b = self.name_tag("b", TAG_B, ROW_B)
        arrow_b = self.link(tag_b, box, TAG_B)
        self.sfx("pop")
        self.play(FadeIn(tag_b, scale=1.3), run_time=0.3)
        self.play(GrowArrow(arrow_b), run_time=0.3)
        if not SHORT:
            self.line(bit, "b = a. So b is a copy\nof a... right?", speech="b equals a. So b is a copy of a... right?")

        self.bar_to(bar, code, 2)
        self.play(Indicate(tag_b, color=TAG_B, scale_factor=1.2), arrow_b.animate.set_stroke(width=11), run_time=0.4)
        self.sfx("pop")
        self.play(self.append_cell(box, 4), arrow_b.animate.set_stroke(width=7), run_time=0.4)
        self.line(bit, "Add 4 to b.\nOnly b. Easy.", speech="Add four to b. Only b. Easy.")

        self.bar_to(bar, code, 3)
        self.console_print(console, "[1, 2, 3, 4]")
        self.moment("surprise")
        self.sfx("oops")
        ring = Circle(radius=0.3, stroke_color="#FF4D4D", stroke_width=7).move_to(console.rows[-1][-2])
        self.play(Create(ring), bit.express("open", "worried"), bit.arms_up(run_time=0.3), run_time=0.4)
        self.line(bit, "WAIT. Why is 4 in a?!\nI never touched a!", speech="Wait. Why is four in a?! I never touched a!")
        self.play(FadeOut(ring), FadeOut(bar), bit.arms_rest(run_time=0.3), run_time=0.3)
        self.tags, self.box, self.arrows = VGroup(tag_a, tag_b), box, VGroup(arrow_a, arrow_b)
        return bit

    def why(self, bit):
        self.moment("payoff")
        self.sfx("ding")
        self.play(self.arrows.animate.set_stroke(width=11), Indicate(self.box, color=ACCENT, scale_factor=1.1),
                  run_time=0.6)
        self.line(bit, "= doesn't copy! b is just a\nsecond name for the SAME list.",
                 speech="Equals doesn't copy! b is just a second name for the same list.")
        self.moment("reveal")
        self.play(self.arrows.animate.set_stroke(width=7), bit.express("flat", "raised"), run_time=0.3)
        self.line(bit, "Two name tags.\nOne list.", speech="Two name tags. One list.")

    def fix(self, bit):
        code, console = self.code, self.console_box
        fixed = self.make_code(COPIED).align_to(code, UL)
        tag_a, tag_b = self.tags
        arrow_b = self.arrows[1]

        # Back to the start: a is [1, 2, 3] again, b's tag waits for its own list.
        self.sfx("whoosh", gain=-6)
        self.play(FadeOut(console.rows), FadeOut(self.box[3]), FadeOut(arrow_b), run_time=0.3)
        self.box.remove(self.box[3])
        console.rows = VGroup()
        self.moment("twist")
        self.sfx("pop")
        self.play(Transform(code.code_lines[1], fixed.code_lines[1]), run_time=0.3)
        self.play(Indicate(code.code_lines[1], color=CONSOLE_GREEN, scale_factor=1.08), run_time=0.5)
        copy = self.list_box([1, 2, 3], ROW_B)
        new_arrow = self.link(tag_b, copy, TAG_B)
        self.sfx("pop")
        self.play(TransformFromCopy(self.box, copy, path_arc=-PI / 3), run_time=0.6)
        self.play(GrowArrow(new_arrow), run_time=0.3)
        self.line(bit, "a.copy() makes a NEW list.\nb gets its own.", gesture=bit.point(1, 75),
                 speech="a dot copy makes a new list. b gets its own.")
        self.play(bit.arms_rest(run_time=0.2), run_time=0.2)
        self.sfx("pop")
        self.play(self.append_cell(copy, 4), run_time=0.4)
        self.console_print(console, "[1, 2, 3]")
        self.sfx("ding")
        self.play(bit.express("grin", "raised"), bit.arms_up(run_time=0.3), Flash(console.rows[-1], color=CONSOLE_GREEN),
                  run_time=0.4)
        self.line(bit, "b got the 4.\na stays safe!", speech="b got the four. a stays safe!")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "Why did a and b\nbreak up?", "They shared\nEVERYTHING.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, Aliasing):
    def design(self):
        """TWO NAMES, ONE LIST: both tags pointing at one box that grew a surprise 4."""
        tag_a = self.name_tag("a", TAG_A, 0).scale(1.6).move_to(pick([-1.0, 0.7, 0], [-2.8, 2.1, 0]))
        tag_b = self.name_tag("b", TAG_B, 0).scale(1.6).move_to(pick([-1.0, -1.9, 0], [-2.8, -0.5, 0]))
        box = VGroup(*[self.cell(v) for v in (1, 2, 3, 4)]).arrange(RIGHT, buff=0).scale(1.5)
        box.move_to(pick([3.9, -0.6, 0], [1.3, 0.8, 0]))
        box[3][0].set_fill("#B00020")
        arrows = VGroup(self.link(tag_a, box, TAG_A), self.link(tag_b, box, TAG_B)).set_stroke(width=12)
        if VERTICAL:  # Reels/Shorts cover: two lines, centered
            words = VGroup(headline_text("WHO ADDED", 110, ACCENT), headline_text("4?!", 170, "#FF4D4D"))
            words.arrange(DOWN, buff=0.1).scale_to_fit_width(7.0).move_to(UP * 4.6)
        else:
            words = headline_text("WHO ADDED 4?!", 120, ACCENT).to_edge(UP, buff=0.5)
        bit = self.shocked_bit(1.35).move_to(pick([-4.9, -1.5, 0], [0, -3.0, 0]))
        self.add(arrows, tag_a, tag_b, box, words, bit)
