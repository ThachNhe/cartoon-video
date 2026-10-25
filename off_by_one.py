"""Off-by-one: a loop that walks one step past the end of a list.

Bit hops along the list's items like stepping stones; `while i <= len(fruits)` makes him step
onto index 3, which does not exist, and he falls into an IndexError. The fix is one character.

Render:  .venv/bin/manim -qh --fps 60 off_by_one.py OffByOne
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 60 off_by_one.py OffByOne
Thumbnail: .venv/bin/manim -s -r 1280,720 off_by_one.py Thumbnail
"""

from bitbybit import *

FRUITS = ["apple", "kiwi", "plum"]
BUGGY = """fruits = ["apple", "kiwi", "plum"]
i = 0
while i <= len(fruits):
    print(fruits[i])
    i += 1"""
FIXED = BUGGY.replace("i <= len", "i < len")
WHILE, PRINT, STEP = 2, 3, 4  # code line numbers (0-based)

SLOT_X0, SLOT_DX = pick(1.6, -2.7), pick(1.45, 1.5)
SLOT_Y = pick(-1.2, -2.4)
BOX_W, BOX_H = 1.3, 0.85


class OffByOne(BitScene):
    code_width = pick(7.2, 7.7)  # the fruits line is long: give the code all the room there is

    # ---------------------------------------------------------------- pieces
    def slot_x(self, k):
        return SLOT_X0 + SLOT_DX * k

    def platform(self):
        """Three fruit boxes with their indexes, and the missing index 3 as a dashed red outline."""
        boxes = VGroup()
        for k, fruit in enumerate(FRUITS):
            box = RoundedRectangle(width=BOX_W, height=BOX_H, corner_radius=0.12, fill_color=FRAME_COLORS[k],
                                   fill_opacity=1, stroke_color=INK, stroke_width=4).move_to([self.slot_x(k), SLOT_Y, 0])
            label = Text(fruit, font=MONO, weight=BOLD, font_size=26, color=INK).move_to(box)
            boxes.add(VGroup(self.shadow(box), box, label))
        indexes = VGroup(*[
            Text(str(k), font=MONO, weight=BOLD, font_size=30, color=TEXT_MUTED).move_to([self.slot_x(k), SLOT_Y - 0.75, 0])
            for k in range(4)
        ])
        indexes[3].set_color("#FF6B6B")
        ghost = DashedVMobject(RoundedRectangle(width=BOX_W, height=BOX_H, corner_radius=0.12, stroke_color="#FF6B6B",
                                                stroke_width=4), num_dashes=24).move_to([self.slot_x(3), SLOT_Y, 0])
        return boxes, indexes, ghost

    def standing_on(self, k):
        """Where Bit's feet go to stand on slot k."""
        return np.array([self.slot_x(k), SLOT_Y + BOX_H / 2, 0])

    def index_error(self):
        return self.error_banner("IndexError:", pick(["list index out of range"], ["list index", "out of range"]))

    def hook_visual(self):
        """The crash: Bit knocked out below the missing slot, the error above."""
        boxes, indexes, ghost = self.platform()
        bit = self.knocked_bit(0.55).rotate(-PI / 3).move_to([self.slot_x(3), SLOT_Y - 1.6, 0])
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0.2)
        return Group(glow, boxes, indexes, ghost, bit, self.index_error().move_to(UP * pick(1.8, 0.9)))

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "Why does this loop crash?")
            self.hook_open(("Why does this loop crash", "on the LAST item?"), "Why does this loop crash on the last item?")
        self.chapter("intro", "Intro")
        bit, title = self.title_intro("OFF-BY-ONE", "Off by one.")
        self.chapter("meet", "The bug that crashes on the last item")
        self.meet(bit, title)
        self.chapter("walk", "Walking the list")
        bit = self.walk(bit)
        self.chapter("why", "Why it crashed: indexes start at 0")
        bit = self.why(bit)
        self.chapter("fix", "The one-character fix")
        self.fix(bit)
        self.chapter("joke", "The off-by-one joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["Count from 0, stop at len - 1."], ["Count from 0,", "stop at len - 1."]),
                    "Click it ONCE.\nNo off-by-one clicks!",
                    loop_line="Wait... did I start\ncounting at 1?", loop_finale=self.hook_look)

    def meet(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: the bug that crashes\non the LAST item. And the fix.", UR, gesture=bit.point(0, 165))
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)

    def walk(self, bit):
        code = self.make_code(BUGGY)
        if VERTICAL:
            code.to_edge(UP, buff=1.7).set_x(0)
        else:
            code.to_corner(UL, buff=0.5).shift(DOWN * 0.35)
        console = self.console(3.6, 1.6).next_to(code, DOWN, buff=0.3, aligned_edge=LEFT)
        boxes, indexes, ghost = self.platform()
        self.code, self.console_box, self.boxes, self.indexes, self.ghost = code, console, boxes, indexes, ghost

        self.play(bit.animate.scale(0.55).move_to(pick([-1.0, -2.6, 0], [-1.0, -4.8, 0])), run_time=0.5)
        self.sfx("whoosh", gain=-4)
        self.play(FadeIn(VGroup(self.shadow(code.background), code), shift=RIGHT * 0.5), FadeIn(console),
                  LaggedStart(*[FadeIn(b, shift=UP * 0.4) for b in boxes], lag_ratio=0.2),
                  FadeIn(indexes[:3]), run_time=0.8)
        self.hop(bit, self.standing_on(0), run_time=0.4)
        self.say(bit, "Three fruits.\nLet's print each one.", UP, shift=RIGHT * 0.3)

        bar = self.line_bar(code, WHILE)
        self.play(FadeIn(bar), bit.look(pick(UL, UP)), run_time=0.25)
        for i in range(3):
            self.bar_to(bar, code, WHILE, run_time=0.2)
            self.bar_to(bar, code, PRINT, run_time=0.2)
            if i:
                self.hop(bit, self.standing_on(i))
            self.console_print(console, FRUITS[i])
            self.bar_to(bar, code, STEP, run_time=0.2)

        # i == 3: the condition still holds...
        self.bar_to(bar, code, WHILE, run_time=0.25)
        self.play(Indicate(code.code_lines[WHILE], color=ACCENT, scale_factor=1.05), run_time=0.5)
        self.say(bit, "Is 3 <= 3? Yep!\nKeep going...", UP, shift=RIGHT * 0.3,
                 speech="Is three less than or equal to three? Yep! Keep going...")
        self.bar_to(bar, code, PRINT, run_time=0.25)
        # ...so Bit steps onto index 3, which does not exist.
        self.play(Create(ghost), FadeIn(indexes[3]), run_time=0.3)
        self.hop(bit, self.standing_on(3), run_time=0.35)
        self.moment("payoff")
        self.sfx("slide_down")
        self.play(bit.animate.shift(DOWN * 6).rotate(-PI / 3), bit.express("open", "worried", run_time=0.2),
                  run_time=0.6, rate_func=rate_functions.ease_in_cubic)
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0)
        banner = self.index_error().move_to(UP * pick(0.6, 0.9))
        self.sfx("crash")
        self.play(FadeIn(banner, scale=2.5), glow.animate.set_fill(opacity=0.2), run_time=0.15, rate_func=rush_into)
        self.shake(strength=0.2, times=5)
        self.wait(0.6)
        self.sfx("whoosh")
        self.play(FadeOut(banner, shift=UP), FadeOut(glow), FadeOut(bar), run_time=0.4)
        self.discard(bit)
        return self.stand(Bit().scale(0.55), self.standing_on(2))

    def why(self, bit):
        self.sfx("boing")
        self.play(FadeIn(bit, shift=DOWN * 0.6), run_time=0.4, rate_func=rate_functions.ease_out_back)
        self.play(bit.express("flat", "worried"), run_time=0.15)
        self.moment("reveal")
        self.play(LaggedStart(*[Indicate(i, color=ACCENT, scale_factor=1.4) for i in self.indexes[:3]], lag_ratio=0.3),
                  run_time=0.8)
        self.say(bit, "3 fruits, but the indexes\nare only 0, 1 and 2.", UP, shift=RIGHT * 0.3,
                 speech="Three fruits, but the indexes are only zero, one and two.")
        self.play(Indicate(self.indexes[3], color=RED, scale_factor=1.5), run_time=0.5)
        self.say(bit, "The last index is len - 1.\n<= walks one step too far.", UP, shift=RIGHT * 0.3,
                 speech="The last index is len minus one. Less-or-equal walks one step too far.")
        return bit

    def fix(self, bit):
        code = self.code
        fixed = self.make_code(FIXED).align_to(code, UL)
        self.moment("twist")
        self.sfx("pop")
        self.play(Transform(code.code_lines[WHILE], fixed.code_lines[WHILE]), run_time=0.3)
        self.play(Indicate(code.code_lines[WHILE], color=CONSOLE_GREEN, scale_factor=1.08), run_time=0.5)
        self.say(bit, "The fix: ONE character.\n< instead of <=.", UP, shift=RIGHT * 0.3, gesture=bit.point(0, 130),
                 speech="The fix: one character. Less-than, instead of less-or-equal.")
        self.play(bit.arms_rest(run_time=0.2), run_time=0.2)

        # Run it again: three hops, then the loop stops at the edge.
        self.sfx("whoosh", gain=-6)
        self.play(FadeOut(self.console_box.rows), FadeOut(self.ghost), FadeOut(self.indexes[3]), run_time=0.3)
        self.console_box.rows = VGroup()
        self.hop(bit, self.standing_on(0), run_time=0.35)
        for i in range(3):
            if i:
                self.hop(bit, self.standing_on(i), run_time=0.22)
            self.console_print(self.console_box, FRUITS[i], run_time=0.15)
        bar = self.line_bar(code, WHILE, color=CONSOLE_GREEN)
        self.play(FadeIn(bar), run_time=0.2)
        self.sfx("ding")
        self.play(bit.express("grin", "raised"), bit.arms_up(run_time=0.3), Flash(bar, color=CONSOLE_GREEN), run_time=0.4)
        self.say(bit, "3 < 3 is False.\nThe loop stops. Safe!", UP, shift=RIGHT * 0.3,
                 speech="Three less than three is false. The loop stops. Safe!")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "There are 2 hard things\nin programming:",
                  "Cache invalidation, naming\nthings, and off-by-one errors.",
                  speech_setup="There are two hard things in programming:")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, OffByOne):
    def design(self):
        """ONE STEP TOO FAR: the fruit stones, the missing index and Bit falling into the gap."""
        boxes, indexes, ghost = self.platform()
        row = VGroup(boxes, indexes, ghost).scale(pick(1.25, 1.2)).move_to(pick([2.3, -2.2, 0], [-0.35, -1.4, 0]))
        bit = self.shocked_bit(1.1).rotate(-0.4).move_to([ghost.get_x() + pick(0.2, -0.2), ghost.get_y() + 1.5, 0])
        words = VGroup(headline_text("ONE STEP", 150, ACCENT), headline_text("TOO FAR!", 150, "#FF4D4D"))
        if VERTICAL:  # Reels/Shorts cover: centered, clear of the cropped top and bottom
            words.arrange(DOWN, buff=0.1).scale_to_fit_width(7.2).move_to(UP * 4.4)
        else:
            words.arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UL, buff=0.55)
        err = Text("IndexError", font=MONO, weight=BOLD, font_size=60, color="#FF6B6B")
        err.set_stroke(INK, 8, background=True).next_to(words, DOWN, buff=0.4, aligned_edge=pick(LEFT, ORIGIN))
        self.add(row, bit, words, err)
