"""Floating point: why 0.1 + 0.2 prints 0.30000000000000004.

Not a Python bug: every language does it (IEEE 754). Binary builds numbers out of halves (1/2, 1/4,
1/8...), and no sum of halves is exactly 0.1, so the computer rounds to the nearest number it can
store: floats are marks on a ruler. 0.3 rounds to one mark, 0.1 + 0.2 lands on the next one.
Compare floats with math.isclose(), never with ==.

Render:  .venv/bin/manim -qh --fps 30 floating_point.py FloatingPoint
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 floating_point.py FloatingPoint
Thumbnail: .venv/bin/manim -s -r 1280,720 floating_point.py Thumbnail
"""

from bitbybit import *

WEIRD = "0.30000000000000004"
JUNK = "#FF6B6B"  # the digits that should not be there
PROMPT = TEXT_MUTED
CONSOLE_AT = pick([-2.4, 0.9, 0], [0, 3.3, 0])
CONSOLE_SIZE = pick((8.0, 3.0), (7.4, 3.0))
BIT_AT = pick([4.9, -1.9, 0], [0, -3.5, 0])
LOOK = pick(LEFT, UP)  # from Bit towards the console and the board
BOARD_AT = pick([-3.4, 0.2, 0], [0, 2.0, 0])  # the explanation's drawings, clear of Bit's speech bubbles
BOARD_W = pick(6.6, 7.2)
HALVES = (("1/16", 1 / 16), ("1/32", 1 / 32), ("1/256", 1 / 256), ("1/512", 1 / 512))  # 0.1 = 0.000110011... in binary
STEP = 0.65  # seconds per halves block
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
        line = VGroup(Text(label, font=MONO, weight=BOLD, font_size=40, color=TEXT_LIGHT),
                      Text(value, font=MONO, weight=BOLD, font_size=40, color=ACCENT))
        line.arrange(RIGHT, buff=0.3, aligned_edge=DOWN).move_to(BOARD_AT)
        self.play(FadeIn(line[0]), run_time=0.2)
        chars = line[1]
        step = run_time / len(chars)
        for k, char in enumerate(chars):
            if k % 3 == 0:
                self.sfx("blip", gain=-10)
            self.play(FadeIn(char, scale=1.5), run_time=step)
        return line

    def chip(self, text, color=ACCENT):
        """A number on a tile."""
        label = Text(text, font=MONO, weight=BOLD, font_size=30, color=color)
        tile = RoundedRectangle(width=label.width + 0.4, height=0.62, corner_radius=0.12, fill_color="#2A2F5E",
                                fill_opacity=1, stroke_color=color, stroke_width=3)
        return VGroup(tile, label.move_to(tile))

    def example(self, text):
        """`text` and a green check mark: a number that binary stores exactly."""
        mark = VMobject(stroke_color=CONSOLE_GREEN, stroke_width=9).set_points_as_corners(
            [[-0.2, 0, 0], [-0.05, -0.17, 0], [0.25, 0.22, 0]])
        return VGroup(Text(text, font=MONO, weight=BOLD, font_size=36, color=TEXT_LIGHT), mark).arrange(RIGHT, buff=0.35)

    def languages(self):
        """The same sum in four other languages prints the same junk digits."""
        cards = VGroup()
        for name in ("JavaScript", "Java", "C#", "Rust"):
            panel = RoundedRectangle(width=pick(3.25, 3.45), height=1.15, corner_radius=0.15, fill_color="#11111B", fill_opacity=1,
                                     stroke_color=GRAY_D, stroke_width=2)
            out = Text(WEIRD, font=MONO, font_size=pick(19, 20), color=CONSOLE_GREEN)
            out[3:].set_color(JUNK)
            label = VGroup(Text(name, font=FONT, weight=BOLD, font_size=26, color=TEXT_LIGHT), out)
            cards.add(VGroup(panel, label.arrange(DOWN, buff=0.16).move_to(panel)))
        cards.arrange_in_grid(2, 2, buff=0.2)
        note = Text("IEEE 754: the same math in every CPU", font=FONT, font_size=24, color=TEXT_MUTED)
        return VGroup(cards, note).arrange(DOWN, buff=0.35).move_to(BOARD_AT)

    def halves(self):
        """What the digits after a binary point are worth: the only pieces a computer builds numbers from."""
        chips = VGroup(*[self.chip(f) for f in ("1/2", "1/4", "1/8", "1/16", "1/32")],
                       Text("…", font=MONO, weight=BOLD, font_size=34, color=ACCENT)).arrange(RIGHT, buff=0.16)
        return chips.move_to(BOARD_AT + UP * 2.1)

    def gauge(self):
        """A bar from 0 to 1/8 with 0.1 marked, the halves that try to fill it, and the running sum.

        Returns (bar, blocks, readouts); readouts has one more entry than blocks: the sum that never ends.
        """
        w = BOARD_W - 0.4
        frame = Rectangle(width=w, height=0.6, stroke_color=TEXT_MUTED, stroke_width=3).set_z_index(1)
        ends = VGroup(*[Text(t, font=MONO, font_size=24, color=TEXT_MUTED).next_to(frame.get_corner(c), DOWN, buff=0.12)
                        for t, c in (("0", DL), ("1/8", DR))])
        x = frame.get_left()[0] + 0.1 * 8 * w
        target = DashedLine([x, -0.45, 0], [x, 0.45, 0], color=ACCENT, stroke_width=5).set_z_index(1)
        goal = Text("0.1", font=MONO, weight=BOLD, font_size=32, color=ACCENT).next_to(target, UP, buff=0.1)

        def readout(terms, total, color=CONSOLE_GREEN):
            return VGroup(Text(terms, font=MONO, font_size=pick(28, 24), color=TEXT_LIGHT),
                          Text(total, font=MONO, weight=BOLD, font_size=pick(32, 28), color=color)).arrange(DOWN, buff=0.15)

        blocks, readouts = VGroup(), VGroup()
        left, total, terms = frame.get_left()[0], 0.0, []
        for k, (name, value) in enumerate(HALVES):
            block = Rectangle(width=w * value * 8, height=0.6, fill_color=FRAME_COLORS[k], fill_opacity=1,
                              stroke_color=INK, stroke_width=2)
            blocks.add(block.move_to([left + block.width / 2, 0, 0]))
            left += block.width
            total += value
            terms.append(name)
            readouts.add(readout(" + ".join(terms), f"= {total}"))
        readouts.add(readout(" + ".join(terms) + " + …", "= 0.0999999999…", JUNK))
        for r in readouts:
            r.next_to(frame, DOWN, buff=0.65)
        shift = BOARD_AT + DOWN * 0.2
        return VGroup(frame, ends, target, goal).shift(shift), blocks.shift(shift), readouts.shift(shift)

    def rounded(self):
        """0.1 and 0.2 as a float really holds them: a hair too big."""
        rows = VGroup()
        for short in (0.1, 0.2):
            stored = f"{short:.20f}"[:21]  # 0.1000000000000000055
            junk = len(stored) - len(stored[3:].lstrip("0"))
            value = Text(stored + "…", font=MONO, font_size=28, color=TEXT_LIGHT)
            value[junk:].set_color(JUNK)
            rows.add(VGroup(Text(str(short), font=MONO, weight=BOLD, font_size=28, color=ACCENT),
                            Text("→", font=MONO, font_size=28, color=TEXT_MUTED), value).arrange(RIGHT, buff=0.25))
        return rows.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to(BOARD_AT + UP * 1.9)

    def ruler(self):
        """The two floats next to 0.3 (17 digits) as ruler marks, and 0.3 itself, 1/5 of the way between them."""
        gap = 0.54 * BOARD_W  # wide enough apart for both 17-digit labels
        line = Line(LEFT * BOARD_W / 2, RIGHT * BOARD_W / 2, stroke_color=TEXT_MUTED, stroke_width=4)
        marks, labels = VGroup(), VGroup()
        for x, value in ((-gap / 2, 0.3), (gap / 2, 0.1 + 0.2)):
            marks.add(Line(DOWN * 0.25, UP * 0.25, stroke_color=TEXT_LIGHT, stroke_width=7).move_to(RIGHT * x))
            labels.add(Text(f"{value:.17g}", font=MONO, font_size=pick(20, 21), color=TEXT_LIGHT)
                       .next_to(marks[-1], DOWN, buff=0.2))
        exact = DashedLine(DOWN * 0.2, UP * 0.2, dash_length=0.06, color=ACCENT, stroke_width=4)
        exact.move_to(RIGHT * (-gap / 2 + 0.2 * gap))
        return VGroup(line, marks, labels, exact).shift(BOARD_AT + DOWN * 0.6)

    def hook_visual(self):
        """First frame of the Short (and the loop's last): the wrong sum, the question and a shocked Bit."""
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0.22)
        question = VGroup(
            Text("Why isn't 0.1 + 0.2", font=FONT, weight=BOLD, font_size=50, color=TEXT_LIGHT),
            Text("equal to 0.3?!", font=FONT, weight=BOLD, font_size=64, color=ACCENT),
        ).arrange(DOWN, buff=0.2).move_to(UP * 3.9)
        if question.width > config.frame_width - 0.6:
            question.scale_to_fit_width(config.frame_width - 0.6)
        console = self.repl().move_to(UP * 0.7)  # below the question
        prompt = Text(">>> 0.1 + 0.2", font=MONO, font_size=40, color=PROMPT)
        result = Text(WEIRD, font=MONO, weight=BOLD, font_size=42, color=CONSOLE_GREEN)
        result[3:].set_color(JUNK)  # the junk after 0.3
        VGroup(prompt, result).arrange(DOWN, aligned_edge=LEFT, buff=0.25).move_to(console[1])
        underline = Line(result[3:].get_corner(DL), result[3:].get_corner(DR), stroke_color="#FF4D4D",
                         stroke_width=6).shift(DOWN * 0.12)
        bit = self.shocked_bit(1.3).move_to(DOWN * 3.3)
        return Group(glow, question, console, prompt, result, underline, bit)

    def cold_open(self):
        """Shorts: the wrong sum and the question are on the very first frame, and Bit asks it at once.

        No title card: the console slides up and the explanation starts from it.
        """
        glow, question, console, prompt, result, underline, bit = self.hook_visual()
        self.add(glow, question, console, prompt, result, underline, bit)
        self.moment("hook")
        self.sfx("oops")
        words = "Why isn't 0.1 + 0.2 equal to 0.3?!"
        spoken = self.voice("Why isn't point one plus point two equal to point three?", captioned=True)
        hold = max(spoken, 1.6) + 0.2
        self.log("text", words, hold + 0.5, words=len(words.split()))  # on screen from frame 0 to the fade out
        self.play(bit.talk(hold), Indicate(result[3:], color="#FF4D4D", scale_factor=1.12, run_time=0.8))

        # Where the console sits for the rest of the video, with the same two lines as its first rows.
        self.moment("topic")
        target = self.repl()
        rows = VGroup(*[
            Text(text, font=MONO, font_size=ROW_SIZE, color=color)
            .next_to(target[2], DOWN, buff=0.12 + 0.36 * ROW_SIZE / 30 * k, aligned_edge=LEFT)
            for k, (text, color) in enumerate(((">>> 0.1 + 0.2", PROMPT), (WEIRD, CONSOLE_GREEN)))
        ])
        rows[1][3:].set_color(JUNK)
        drop = bit[-1]  # shocked_bit()'s sweat drop
        bit.remove(drop)
        self.sfx("whoosh")
        self.play(FadeOut(question, shift=UP * 0.6), FadeOut(glow), FadeOut(underline), FadeOut(drop),
                  Transform(console, target), ReplacementTransform(prompt, rows[0]),
                  ReplacementTransform(result, rows[1]), bit.animate.scale(0.8 / 1.3).move_to(BIT_AT), run_time=0.5)
        self.remove(*rows)
        console.rows = rows
        self.add(rows)
        self.play(bit.express("flat", "raised"), bit.look(UP), run_time=0.25)
        return bit, console

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "Why isn't 0.1 + 0.2 equal to 0.3?")
            bit, console = self.cold_open()
        else:
            self.chapter("intro", "Intro")
            bit, title = self.title_intro("0.1 + 0.2 = ?", "Zero point one, plus zero point two.")
            self.chapter("weird", "The weird answer")
            bit, console = self.weird(bit, title)
        self.chapter("why", "Why: computers count in halves")
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
        """16:9 only (the Short opens on this answer): Bit runs 0.1 + 0.2 and gets the weird result."""
        self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
        self.moment("promise")
        self.say(bit, "Today: why computers can't add\n0.1 + 0.2. And the fix.", UR, gesture=bit.point(0, 165),
                 speech="Today: why computers can't add zero point one plus zero point two. And the fix.")
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.8).move_to(BIT_AT), run_time=0.4)
        console = self.repl()
        self.play(FadeIn(console, shift=DOWN * 0.3), bit.look(LEFT), run_time=0.4)
        self.say(bit, "Easy one. 0.1 + 0.2...", UP, speech="Easy one. Zero point one plus zero point two...")
        result = self.run(console, "0.1 + 0.2", WEIRD)
        self.moment("surprise")
        self.sfx("oops")
        junk = result[3:]
        underline = Line(junk.get_corner(DL), junk.get_corner(DR), stroke_color="#FF4D4D", stroke_width=6).shift(DOWN * 0.1)
        self.play(junk.animate.set_color(JUNK), Create(underline), bit.express("open", "worried"),
                  bit.arms_up(run_time=0.3), run_time=0.4)
        self.say(bit, "0.30000000000000004?!\nPython can't do math?!", UP,
                 speech="Zero point three, and then a four?! Python can't do math?!")
        self.play(FadeOut(underline), bit.arms_rest(run_time=0.3), bit.express("flat", "raised"), run_time=0.3)
        return bit, console

    def why(self, bit, console):
        # The explanation gets the whole stage; the console comes back for the proof.
        self.sfx("whoosh", gain=-4)
        self.play(FadeOut(console), FadeOut(console.rows), bit.look(LOOK), run_time=0.3)

        # Not Python's fault: every language prints the same digits.
        cards, note = langs = self.languages()
        for k in range(len(cards)):
            self.sfx("pop", offset=0.25 + 0.35 * k, gain=-6)
        self.moment("surprise")
        self.say(bit, "Not a Python bug.\nEVERY language does this!", UP,
                 gesture=LaggedStart(*[FadeIn(card, scale=0.8) for card in cards], FadeIn(note), lag_ratio=0.45,
                                     run_time=2.2))
        if not SHORT:
            self.say(bit, "They all follow one standard,\nbuilt into the processor.", UP)
        self.sfx("whoosh", gain=-6)
        self.play(FadeOut(langs, shift=UP * 0.3), run_time=0.3)

        # Binary builds numbers out of halves...
        chips = self.halves()
        self.say(bit, "Computers count in binary:\nhalves, quarters, eighths.", UP,
                 gesture=LaggedStart(*[FadeIn(c, shift=DOWN * 0.3) for c in chips], lag_ratio=0.3, run_time=1.5))
        easy = [("0.5 = 1/2", "0.5? That's just 1/2. Easy!", "Point five? That's just one half. Easy!")]
        if not SHORT:
            easy.append(("0.75 = 1/2 + 1/4", "0.75? 1/2 + 1/4.\nAlso easy!",
                         "Point seven five? One half plus one quarter. Also easy!"))
        rows = VGroup()
        for k, (sum_, line, speech) in enumerate(easy):
            row = self.example(sum_).move_to(BOARD_AT + UP * (0.9 - 0.8 * k))
            rows.add(row)
            self.play(FadeIn(row[0], shift=RIGHT * 0.2), run_time=0.3)
            self.sfx("ding", offset=0.25, gain=-4)
            self.say(bit, line, UP, speech=speech, gesture=Create(row[1], run_time=0.4))

        # ...and no sum of halves is exactly 0.1.
        self.sfx("whoosh", gain=-6)
        self.play(FadeOut(rows), run_time=0.3)
        bar, blocks, readouts = self.gauge()
        self.play(FadeIn(bar), run_time=0.3)
        self.add(blocks.set_opacity(0), readouts.set_opacity(0))

        def build(_, alpha):
            k = min(len(readouts) - 1, int(alpha * len(readouts)))
            for i, block in enumerate(blocks):
                block.set_opacity(1 if i <= k else 0)
            for i, readout in enumerate(readouts):
                readout.set_opacity(1 if i == k else 0)

        for k in range(len(blocks)):
            self.sfx("pop", offset=0.25 + STEP * k, gain=-4)
        self.sfx("oops", offset=0.25 + STEP * len(blocks), gain=-6)
        self.moment("reveal")
        self.say(bit, "But 0.1? 1/16 + 1/32 + …\nIt NEVER ends!", UP,
                 speech="But point one? One sixteenth, plus one thirty-second, plus... It never ends!",
                 gesture=UpdateFromAlphaFunc(VGroup(blocks, readouts), build, run_time=STEP * len(readouts),
                                             rate_func=linear))
        self.sfx("whoosh", gain=-4)
        if SHORT:
            self.play(*[FadeOut(m) for m in (chips, bar, blocks, readouts)], run_time=0.3)
        else:
            self.play(*[FadeOut(m) for m in (bar, blocks, readouts)], run_time=0.3)
            self.say(bit, "Like 1/3 in decimal.", UP, speech="It's like one third in decimal.")
            third = self.digits("1/3 =", "0.33333333333…")
            self.say(bit, "You can never write it ALL.\nYou have to stop SOMEWHERE.", UP)
            self.sfx("whoosh", gain=-4)
            self.play(FadeOut(chips), FadeOut(third), run_time=0.3)

        # Bits run out, so it rounds to the nearest number it CAN store: floats are marks on a ruler.
        self.chapter("round", "Rounding: floats are marks on a ruler")
        stored = self.rounded()
        if not SHORT:
            self.say(bit, "A float has only 64 bits.\nSo it stops and ROUNDS.", UP)
        self.say(bit, pick("0.1 becomes a tiny bit MORE.\nSo does 0.2.", "Bits run out, so it ROUNDS.\n0.1 becomes a tiny bit MORE."),
                 UP, speech=pick("Point one becomes a tiny bit more. So does point two.",
                                 "Bits run out, so it rounds. Point one becomes a tiny bit more."),
                 gesture=LaggedStart(*[FadeIn(row, shift=RIGHT * 0.3) for row in stored], lag_ratio=0.5, run_time=1.2))

        ruler = self.ruler()
        (a, b), exact = ruler[1], ruler[3]
        three, total = self.chip("0.3"), self.chip("0.1 + 0.2", JUNK)
        three.next_to(exact, UP, buff=0.9)
        total.next_to(b, UP, buff=0.9)
        self.sfx("whoosh", gain=-6)
        self.play(FadeIn(ruler), FadeIn(three, shift=DOWN * 0.2), run_time=0.4)
        self.sfx("pop", offset=0.25 + 2.1)
        self.say(bit, "Floats are like ruler marks.\n0.3 snaps to the NEAREST one.", UP,
                 speech="Floats are like ruler marks. Point three snaps to the nearest one.",
                 gesture=Succession(Wait(1.6), three.animate(run_time=0.5).next_to(a, UP, buff=0.1)))
        self.play(FadeIn(total, shift=DOWN * 0.2), run_time=0.3)
        self.sfx("pop", offset=0.25 + 2.3)
        self.say(bit, "0.1 + 0.2 was rounded UP,\nso it lands on the NEXT one!", UP,
                 speech="Point one plus point two got rounded up, so it lands on the next one!",
                 gesture=Succession(Wait(1.8), total.animate(run_time=0.5).next_to(b, UP, buff=0.1)))
        unequal = Text("≠", font=MONO, weight=BOLD, font_size=80, color=JUNK).move_to([ruler.get_x(), three.get_y(), 0])
        self.moment("reveal")
        self.sfx("oops")
        self.play(FadeIn(unequal, scale=1.6), bit.express("open", "worried"), run_time=0.4)
        self.wait(0.3)

        # The proof, back in Python.
        self.sfx("whoosh", gain=-4)
        self.play(*[FadeOut(m) for m in (stored, ruler, three, total, unequal)], FadeIn(console), FadeIn(console.rows),
                  bit.express("flat", "raised"), run_time=0.4)
        result = self.run(console, "0.1 + 0.2 == 0.3", "False", color=JUNK)
        self.moment("payoff")
        self.sfx("crash")
        self.play(Indicate(result, color="#FF4D4D", scale_factor=1.6), bit.express("open", "worried"), run_time=0.5)
        self.shake(strength=0.12, times=4)
        self.say(bit, "Two different marks.\nSo == says False!", UP, speech="Two different marks. So equals-equals says false!")

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
