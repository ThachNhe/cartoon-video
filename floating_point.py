"""Floating point: why 0.1 + 0.2 prints 0.30000000000000004.

1/3 never ends in decimal; 0.1 never ends in binary, so Python stores a rounded value and the
tiny errors add up. Compare floats with math.isclose(), never with ==.

Render:  .venv/bin/manim -qh --fps 30 floating_point.py FloatingPoint
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 floating_point.py FloatingPoint
Thumbnail: .venv/bin/manim -s -r 1280,720 floating_point.py Thumbnail
"""

from bitbybit import *

WEIRD = "0.30000000000000004"
PROMPT = TEXT_MUTED
CONSOLE_AT = pick([-2.4, 0.9, 0], [0, 3.3, 0])
CONSOLE_SIZE = pick((8.0, 3.0), (7.4, 3.0))
DIGITS_AT = pick([-2.4, -2.3, 0], [0, 0.5, 0])
BIT_AT = pick([4.9, -1.9, 0], [0, -3.5, 0])
ROW_SIZE = pick(32, 30)  # console text; the isclose() line has to fit the 9:16 width


class FloatingPoint(BitScene):
    # ---------------------------------------------------------------- pieces
    def repl(self):
        console = self.console(*CONSOLE_SIZE).move_to(CONSOLE_AT)
        console[2].become(Text("PYTHON", font=MONO, font_size=20, color=GRAY_B).move_to(console[2], aligned_edge=LEFT))
        return console

    def run(self, console, command, result=None, color=CONSOLE_GREEN):
        """Type `command` at the prompt, then print `result` (if it has one)."""
        self.console_print(console, f">>> {command}", color=PROMPT, run_time=0.3, font_size=ROW_SIZE)
        if result:
            self.console_print(console, result, color=color, run_time=0.25, font_size=ROW_SIZE)
        return console.rows[-1]

    def digits(self, label, value, run_time=1.6):
        """Write `value` one character at a time after `label`: a number that never ends."""
        line = VGroup(Text(label, font=MONO, weight=BOLD, font_size=pick(40, 36), color=TEXT_LIGHT),
                      Text(value, font=MONO, weight=BOLD, font_size=pick(40, 36), color=ACCENT))
        line.arrange(pick(RIGHT, DOWN), buff=0.3, aligned_edge=pick(DOWN, LEFT)).move_to(DIGITS_AT)
        self.play(FadeIn(line[0]), run_time=0.2)
        chars = line[1]
        step = run_time / len(chars)
        for k, char in enumerate(chars):
            if k % 3 == 0:
                self.sfx("blip", gain=-10)
            self.play(FadeIn(char, scale=1.5), run_time=step)
        return line

    def hook_visual(self):
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0.22)
        console = self.repl().move_to(UP * 0.7)  # below the hook question
        prompt = Text(">>> 0.1 + 0.2", font=MONO, font_size=40, color=PROMPT)
        result = Text(WEIRD, font=MONO, weight=BOLD, font_size=42, color=CONSOLE_GREEN)
        result[3:].set_color("#FF6B6B")  # the junk after 0.3
        VGroup(prompt, result).arrange(DOWN, aligned_edge=LEFT, buff=0.25).move_to(console[1])
        underline = Line(result[3:].get_corner(DL), result[3:].get_corner(DR), stroke_color="#FF4D4D",
                         stroke_width=6).shift(DOWN * 0.12)
        bit = self.shocked_bit(1.3).move_to(DOWN * 3.3)
        return Group(glow, console, prompt, result, underline, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "Why is 0.1 + 0.2 wrong?")
            self.hook_open(("Why can't Python", "add 0.1 + 0.2?!"), "Why can't Python add point one plus point two?",
                           sound="oops", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.title_intro("0.1 + 0.2 = ?", "Zero point one, plus zero point two.")
        self.chapter("weird", "The weird answer")
        bit, console = self.weird(bit, title)
        self.chapter("why", "Why: numbers that never end in binary")
        self.why(bit, console)
        self.chapter("fix", "The fix: math.isclose")
        self.fix(bit, console)
        self.chapter("joke", "The floating point joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["Never compare floats with ==."], ["Never compare", "floats with =="]),
                    "One click.\nNot 0.9999999 clicks.",
                    loop_line="So... what IS\n0.1 + 0.2?", loop_finale=self.hook_look)

    def weird(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: why computers can't add\n0.1 + 0.2. And the fix.", UR, gesture=bit.point(0, 165),
                     speech="Today: why computers can't add zero point one plus zero point two. And the fix.")
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.8).move_to(BIT_AT), run_time=0.4)
        console = self.repl()
        self.play(FadeIn(console, shift=DOWN * 0.3), bit.look(pick(LEFT, UP)), run_time=0.4)
        self.say(bit, "Easy one. 0.1 + 0.2...", UP, speech="Easy one. Zero point one plus zero point two...")
        result = self.run(console, "0.1 + 0.2", WEIRD)
        self.moment("surprise")
        self.sfx("oops")
        junk = result[3:]
        underline = Line(junk.get_corner(DL), junk.get_corner(DR), stroke_color="#FF4D4D", stroke_width=6).shift(DOWN * 0.1)
        self.play(junk.animate.set_color("#FF6B6B"), Create(underline), bit.express("open", "worried"),
                  bit.arms_up(run_time=0.3), run_time=0.4)
        self.say(bit, "0.30000000000000004?!\nPython can't do math?!", UP,
                 speech="Zero point three, and then a four?! Python can't do math?!")
        self.play(FadeOut(underline), bit.arms_rest(run_time=0.3), bit.express("flat", "raised"), run_time=0.3)
        return bit, console

    def why(self, bit, console):
        self.say(bit, "Try writing 1/3\nin decimal.", UP, speech="Try writing one third in decimal.")
        third = self.digits("1/3 =", "0.33333333333…")
        if not SHORT:
            self.say(bit, "It never ends.\nYou have to stop SOMEWHERE.", UP)
        self.sfx("whoosh", gain=-4)
        self.play(FadeOut(third), run_time=0.3)
        self.moment("reveal")
        self.say(bit, "Computers count in binary.\nIn binary, 0.1 never ends!", UP,
                 speech="Computers count in binary. And in binary, zero point one never ends!")
        tenth = self.digits("0.1 =", "0.000110011001100…")
        cut = DashedLine(UP * 0.45, DOWN * 0.45, color="#FF4D4D", stroke_width=6).next_to(tenth[1], RIGHT, buff=0.1)
        self.sfx("pop")
        self.play(Create(cut), Indicate(tenth[1], color="#FF6B6B", scale_factor=1.05), run_time=0.5)
        if not SHORT:
            self.say(bit, "So Python rounds it.\nA tiny error sneaks in.", UP)
        self.sfx("whoosh", gain=-4)
        self.play(FadeOut(tenth), FadeOut(cut), run_time=0.3)

        # The errors of 0.1 and 0.2 add up: the sum is not the stored 0.3.
        result = self.run(console, "0.1 + 0.2 == 0.3", "False", color="#FF6B6B")
        self.moment("payoff")
        self.sfx("crash")
        self.play(Indicate(result, color="#FF4D4D", scale_factor=1.6), bit.express("open", "worried"), run_time=0.5)
        self.shake(strength=0.12, times=4)
        self.say(bit, "Two tiny errors add up.\nSo == says False!", UP, speech="Two tiny errors add up. So equals-equals says false!")

    def fix(self, bit, console):
        self.moment("twist")
        self.sfx("whoosh", gain=-6)
        self.play(FadeOut(console.rows), run_time=0.3)
        console.rows = VGroup()
        self.run(console, "from math import isclose")
        result = self.run(console, "isclose(0.1 + 0.2, 0.3)", "True")
        self.sfx("ding")
        self.play(Indicate(result, color=CONSOLE_GREEN, scale_factor=1.6), bit.express("grin", "raised"),
                  bit.arms_up(run_time=0.3), run_time=0.5)
        self.say(bit, "Compare floats with isclose,\nnot with ==.", UP, speech="Compare floats with is-close, not with equals-equals.")
        if not SHORT:
            self.say(bit, "Money? Count whole cents\nwith integers instead.", UP)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "My bank stores my money\nin floats.", "Now I have\n$0.30000000000000004.",
                  speech_punch="Now I have thirty cents. And a tiny bit more.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, FloatingPoint):
    def design(self):
        """0.1 + 0.2 = 0.30000000000000004 with the junk digits in red and a shocked Bit."""
        sum_ = headline_text("0.1 + 0.2 =", 120, TEXT_LIGHT)
        if VERTICAL:  # Reels/Shorts cover: centered, clear of the cropped top and bottom
            sum_.scale_to_fit_width(7.0).move_to(UP * 4.9)
        else:
            sum_.to_corner(UL, buff=0.6).shift(DOWN * 0.2)
        answer = Text(WEIRD, font=MONO, weight=BOLD, font_size=88, color=ACCENT)
        answer[3:].set_color("#FF4D4D")
        answer.set_stroke(INK, 12, background=True).scale_to_fit_width(config.frame_width - pick(1.2, 0.8))
        answer.next_to(sum_, DOWN, buff=0.35, aligned_edge=pick(LEFT, ORIGIN))
        bit = self.shocked_bit(1.35).move_to(pick([4.7, -2.0, 0], [0, -2.8, 0]))
        tag = headline_text("WHY?!", 120, "#FF4D4D").move_to(pick([-2.8, -2.4, 0], [0, 1.2, 0]))
        if VERTICAL:
            tag.scale_to_fit_width(6.4)
        self.add(sum_, answer, bit, tag)
