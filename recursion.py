"""Recursion: a standalone cartoon about recursion and the base case.

The shared parts (Bit, branding, narrator, sound effects, the subscribe ending) live in bitbybit.py.

Render:  .venv/bin/manim -qh --fps 30 recursion.py Recursion
Preview: .venv/bin/manim -ql recursion.py Recursion
Set BIT_VOICE=0 to render without narration.

Vertical 9:16 for YouTube Shorts / Facebook Reels (lands in media/videos/recursion/1920p30/).
It opens on a hook and uses a tighter cut than the 16:9 video:
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 recursion.py Recursion

Channel avatar (2048x2048 PNG; the round one has a transparent outside):
    .venv/bin/manim -s -r 2048,2048 recursion.py ChannelAvatar
    .venv/bin/manim -s -t -r 2048,2048 recursion.py ChannelAvatarRound

YouTube thumbnail (1280x720; ThumbnailCode and ThumbnailStack are alternatives):
    .venv/bin/manim -s -r 1280,720 recursion.py Thumbnail
"""

from bitbybit import *


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

CODE_WIDTH = pick(6.2, 7.2)
CODE_DIR = pick(UL, UP)  # where Bit looks to read the code
STACK_X = pick(4.6, 1.85)
STACK_BASE_Y = pick(-3.3, -4.6)
STACK_TOP_Y = pick(2.9, 0.8)  # past this, new frames push the stack down
FRAME_STEP = 0.68


class Recursion(BitScene):
    code_width = CODE_WIDTH
    code_reference = COUNTDOWN

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
        if SHORT:
            self.chapter("cold_open", "What happens if you delete one line?")
            self.cold_open()
        self.chapter("intro", "Intro")
        bit, title = self.intro()
        self.chapter("meet_bit", "What is recursion?")
        bit = self.meet_bit(bit, title)
        self.chapter("happy_path", "Countdown and the call stack")
        bit, code = self.happy_path(bit)
        self.chapter("stack_overflow", "Deleting the base case: stack overflow")
        self.stack_overflow(bit, code)
        self.chapter("punchline", "The recursion joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.outro()

    def crash_banner(self):
        return self.error_banner("RecursionError:", pick(["maximum recursion depth exceeded"],
                                                          ["maximum recursion", "depth exceeded"]))

    def cold_open(self):
        """Hook for Shorts/Reels: flash the crash from the end, then ask the question that leads to it."""
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0.2)
        bit = Bit().move_to(DOWN * 2.4)
        banner = self.crash_banner().move_to(UP * 0.9)
        hook = VGroup(
            Text("What happens if you", font=FONT, weight=BOLD, font_size=50, color=TEXT_LIGHT),
            Text("delete ONE line?", font=FONT, weight=BOLD, font_size=64, color=ACCENT),
        ).arrange(DOWN, buff=0.2).move_to(UP * 3.9)

        # The very first frame (the feed's preview) is already the crash.
        for knocked_out in (bit.x_eyes(), bit.set_mouth("open")):
            knocked_out.begin()
            knocked_out.finish()
        self.add(glow, bit, banner)
        self.moment("hook")
        self.sfx("crash")
        self.shake(strength=0.2, times=5)
        self.sfx("whoosh", gain=-6)
        self.play(FadeIn(hook, shift=DOWN * 0.3), run_time=0.25)
        spoken = self.voice("What happens if you delete one line?", captioned=True)
        hold = max(spoken, 1.6) + 0.3
        self.log("text", "What happens if you delete ONE line?", 0.25 + hold + 0.3, words=7)  # fade in, hold, fade out
        self.wait(hold)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.3)
        self.stage()

    def intro(self):
        """Bit types the title on a laptop, typos it, and fixes it."""
        size = pick(120, 80)
        final = Text("RECURSION", font=FONT, weight=BOLD, font_size=size, color=HEADLINE).move_to(UP * pick(2.0, 3.0))
        typo = Text("RECURSOIN", font=FONT, weight=BOLD, font_size=size, color=HEADLINE)
        typo.align_to(final, LEFT).align_to(final, DOWN)
        bit = Bit().move_to(DOWN * 1.7)
        laptop = self.laptop()
        laptop.shift(UP * (-2.45 - laptop[1].get_top()[1]))  # lid hides Bit's belly, hands rest on its edge

        self.sfx("whoosh")
        self.play(FadeIn(bit, shift=UP * 1.5), FadeIn(laptop, shift=UP * 1.5), run_time=0.5,
                  rate_func=rate_functions.ease_out_back)
        if not SHORT:
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
        if not SHORT:
            self.wait(0.3)

        # R E C U R S O I N ... with a typist's uneven rhythm.
        pauses = [0.05, 0.02, 0.08, 0.02, 0.03, 0.12, 0.02, 0.03, 0.0]
        if SHORT:
            # No typo gag: the hook already used up the first seconds.
            for k, letter in enumerate(final):
                keystroke(k, letter, pause=pauses[k] / 2)
            title = final
        else:
            for k, letter in enumerate(typo):
                keystroke(k, letter, pause=pauses[k])

            # Spellcheck catches it; Bit freezes and looks at us.
            squiggle = ParametricFunction(
                lambda t: np.array([t, 0.07 * np.sin(t * 26), 0]), t_range=[0, VGroup(*typo[6:]).width],
                stroke_color=RED, stroke_width=6,
            ).next_to(VGroup(*typo[6:]), DOWN, buff=0.12)
            self.wait(0.25)
            self.moment("gag")
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
            title = VGroup(*typo[:6], *final[6:])

        # Done. Ding!
        for letter in title:
            self.remove(letter)
        self.add(title)
        cursor.clear_updaters()
        self.remove(cursor)
        self.sfx("ding")
        self.play(title.animate(rate_func=there_and_back).scale(1.06), bit.look(ORIGIN), bit.express("grin", "smug"),
                  run_time=0.35)
        self.moment("topic")
        spoken = self.voice("Recursion.", captioned=True)  # the title is on screen
        self.play(bit.talk(max(spoken, 0.5)))

        self.sfx("whoosh")
        self.play(FadeOut(laptop, shift=DOWN * 2), run_time=0.4, rate_func=rush_into)
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        return bit, title

    def meet_bit(self, bit, title):
        if SHORT:
            self.say(bit, "Recursion is when a\nfunction calls ITSELF.", UR, gesture=bit.point(0, 165))
            self.sfx("whoosh")
            self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.3)
            return bit
        self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
        self.play(bit.set_mouth("grin"), run_time=0.2)
        # Within 15 seconds, promise what the viewer gets for staying.
        self.moment("promise")
        self.say(bit, "Today: RECURSION, and the ONE\nline that stops it from CRASHING.", UR, gesture=bit.point(0, 165))
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
        code = self.make_code(COUNTDOWN)
        if VERTICAL:
            # Code across the top; output (left) and call stack (right) share the space below.
            code.to_edge(UP, buff=1.7).set_x(0)
        else:
            code.to_corner(UL, buff=0.5).shift(DOWN * 0.35)
        panel = RoundedRectangle(
            width=pick(code.width, 3.4), height=1.95, corner_radius=0.15,
            fill_color="#11111B", fill_opacity=1, stroke_color=GRAY_D, stroke_width=2,
        ).next_to(code, DOWN, buff=0.3, aligned_edge=LEFT)
        panel_label = Text("OUTPUT", font=MONO, font_size=20, color=GRAY_B).next_to(
            panel.get_corner(UL), DR, buff=0.15)
        stack_title = Text("CALL STACK", font=FONT, weight=BOLD, font_size=26, color=TEXT_MUTED).move_to(
            [STACK_X, STACK_BASE_Y - 0.35, 0])
        base = Line([STACK_X - 1.8, STACK_BASE_Y, 0], [STACK_X + 1.8, STACK_BASE_Y, 0], color=TEXT_MUTED, stroke_width=5)
        code_shadow, panel_shadow = self.shadow(code.background), self.shadow(panel)

        self.play(bit.animate.scale(0.7).move_to(pick([1.4, -2.55, 0], [-2.0, -3.3, 0])), run_time=0.6)
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
        self.play(FadeIn(bar), bit.look(CODE_DIR), run_time=0.3)

        for n in (3, 2, 1, 0):
            slow = n == 3
            step = 0.35 if slow else 0.2
            self.bar_to(bar, code, 0, run_time=step)
            push(n, run_time=0.35 if slow else 0.25)
            if slow:
                self.play(bit.look(RIGHT), run_time=0.15)
                self.say(bit, "Every call gets its own\nbox on the call stack.", UP, shift=RIGHT * 0.4,
                         gesture=bit.point(1, 75))
                self.play(bit.look(CODE_DIR), bit.arms_rest(run_time=0.25), run_time=0.25)
            self.bar_to(bar, code, 1, run_time=step)
            if slow and not SHORT:
                self.say(bit, "Is n == 0? Nope, it's 3.\nKeep going!", UP, shift=RIGHT * 0.4,
                         speech="Is n equal to zero? Nope, it's three. Keep going!")
            if n > 0:
                self.bar_to(bar, code, 4, run_time=step)
                print_line(str(n))
                self.bar_to(bar, code, 5, run_time=step)
                if slow and not SHORT:
                    self.say(bit, "...and now it calls\nITSELF with n - 1.", UP, shift=RIGHT * 0.4,
                             speech="And now, it calls itself, with n minus one.")
            else:
                self.bar_to(bar, code, 2, run_time=step)
                self.play(bit.express("grin", "raised"), bit.arms_up(run_time=0.3), run_time=0.3)
                print_line("Liftoff!", color=ACCENT, run_time=0.3)
                self.moment("reveal")
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
        if SHORT:  # phone-sized: the highlight already shows which line
            self.say(bit, "That line is the BASE CASE:\nthe exit door.", UP, shift=RIGHT * 0.4, gesture=bit.point(0, 125))
        else:
            self.say(bit, "That  if n == 0  line is the\nBASE CASE. It's the exit door.", UP, shift=RIGHT * 0.4,
                     speech="That, if n equals zero, line is the base case. It's the exit door.",
                     gesture=bit.point(0, 125))
        self.play(bit.express("smug", "smug"), bit.arms_rest(run_time=0.25), run_time=0.25)
        self.say(bit, "Now... what if we\nDELETE the exit door?", UP, shift=RIGHT * 0.4)

        # Strike out the base case and throw it off screen.
        self.moment("twist")
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
        ).move_to(pick([1.4, 3.35, 0], [STACK_X, STACK_TOP_Y + 0.6, 0])))
        self.play(FadeIn(depth_label), bit.express("smile", "neutral"), bit.look(CODE_DIR), run_time=0.3)

        bar = self.line_bar(code, 0)
        self.add(bar)
        next_y = STACK_BASE_Y + 0.36
        offscreen = -config.frame_height / 2 - 0.3  # frames below this have scrolled away

        for k, n in enumerate(range(3, -36, -1)):
            run_time = max(0.06, 0.4 * 0.8 ** k)
            frame = self.stack_frame(n, FRAME_COLORS[k % len(FRAME_COLORS)])
            anims = [bar.animate.set_y(code.code_lines[k % 3].get_y())]
            if next_y > STACK_TOP_Y:
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
                if f.get_top()[1] < offscreen and f in stack:
                    stack.remove(f)

            if n == 0:
                if not SHORT:
                    self.say(bit, "Okay, n is 0, so we... wait.", UP, shift=RIGHT * 0.4,
                             speech="Okay, n is zero, so we... wait.")
                self.play(bit.express("flat", "raised"), run_time=0.15)
            elif n == -2:
                self.play(bit.express("open", "worried"), bit.look(UR), bit.arms_up(run_time=0.2), run_time=0.2)
                self.moment("surprise")
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
                if f is not base and f.get_top()[1] < offscreen:
                    stack.remove(f)

        # Crash.
        banner = self.crash_banner().move_to(UP * 0.6)
        self.moment("payoff")
        self.sfx("crash")
        self.play(FadeIn(banner, scale=2.5), alarm_glow.animate.set_fill(opacity=0.25), run_time=0.15, rate_func=rush_into)
        self.shake(strength=0.2, times=7)
        self.play(bit.x_eyes(), bit.set_mouth("open"), run_time=0.15)
        self.sfx("slide_down")
        self.play(Rotate(bit, -PI / 2, about_point=bit.get_corner(DR)), run_time=0.6, rate_func=rate_functions.ease_in_cubic)
        self.sfx("boing")
        self.shake(strength=0.08, times=3)
        self.wait(0.6 if SHORT else 1.2)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.6)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.6, -0.6, 0], [-1.8, -1.4, 0]))
        bandage = VGroup(*[
            RoundedRectangle(width=0.5, height=0.16, corner_radius=0.06, fill_color="#F5D6A8",
                             fill_opacity=1, stroke_color="#C9A27A", stroke_width=2).rotate(a)
            for a in (PI / 4, -PI / 4)
        ]).move_to(bit.face_point(0.6, 0.9))
        bit.add(bandage)
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.5)
        self.play(bit.blink())
        self.play(bit.express("flat", "worried"), run_time=0.15)
        if not SHORT:  # the outro headline carries the lesson in the short cut
            self.say(bit, "Lesson learned:\nALWAYS write a base case.", UR)
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        if not SHORT:
            self.say(bit, "Here's a little joke,\nso you never forget.", UR)
        bubble = self.say(bit, "To understand recursion,\nyou must first understand\nrecursion.",
                          UR, keep=True)
        self.play(bit.express("grin", "raised"), run_time=0.15)
        self.moment("joke")
        self.sfx("rimshot_ba")
        self.sfx("rimshot_dum", offset=0.18)
        self.sfx("rimshot_tss", offset=0.4)
        self.wait(1.0)

        # The joke recurses: zoom into an endless tunnel of itself.
        border = Rectangle(width=config.frame_width - 0.3, height=config.frame_height - 0.3,
                           stroke_color=TEXT_LIGHT, stroke_width=6)
        self.play(Create(border), run_time=0.4)
        world = VGroup(border, bit, bubble)
        pivot = np.array(pick([4.6, -2.3, 0], [2.0, -4.2, 0]))
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
        for _ in range(2 if SHORT else 3):
            deeper = world.copy().scale(ratio ** (len(copies) + 1), about_point=pivot)
            copies.append(deeper)
            tunnel.add(deeper)
            self.add(deeper)
            self.play(tunnel.animate.scale(1 / ratio, about_point=pivot), run_time=0.9, rate_func=linear)
        self.play(FadeOut(tunnel), run_time=0.4)
        self.stage()

    def outro(self):
        self.ending(pick(["Always write your base case."], ["Always write", "your base case."]),
                    "Base case reached.\nThe video can end now.",
                    loop_line="...unless someone deletes\nthe base case.")


class Thumbnail(ThumbnailMixin, Recursion):
    def design(self):
        """1 LINE = CRASH: the struck-out base case, the error, and a panicking Bit."""
        for radius, opacity in ((4.2, 0.10), (3.0, 0.12), (1.9, 0.14)):
            self.add(Circle(radius=radius, fill_color=RED, fill_opacity=opacity, stroke_width=0)
                     .move_to(pick([3.6, -0.6, 0], [0, -2.2, 0])))
        self.add(self.crash_banner().scale(0.5).rotate(10 * DEGREES).move_to(pick([3.3, 2.6, 0], [0.3, 0.0, 0])))
        self.add(self.shocked_bit(1.75).move_to(pick([3.7, -1.3, 0], [0, -3.1, 0])))
        words = VGroup(headline_text("1 LINE", 170, ACCENT), headline_text("= CRASH", 150, "#FF4D4D"))
        if VERTICAL:  # Reels/Shorts cover: centered, clear of the cropped top and bottom
            words.arrange(DOWN, buff=0.15).scale_to_fit_width(7.2).move_to(UP * 4.6)
        else:
            words.arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(UL, buff=0.6).shift(DOWN * 0.4)
        line = Text("if n == 0:", font=MONO, weight=BOLD, font_size=64, color=TEXT_LIGHT)
        line.next_to(words, DOWN, buff=0.55, aligned_edge=pick(LEFT, ORIGIN)).shift(pick(RIGHT * 0.1, ORIGIN))
        strike = Line(line.get_left() + LEFT * 0.15, line.get_right() + RIGHT * 0.15, stroke_color=RED, stroke_width=14)
        self.add(words, line, strike)


class ThumbnailCode(Thumbnail):
    """DON'T DELETE THIS: the countdown code with the base case circled, Bit pointing at it."""

    def design(self):
        code = self.make_code(COUNTDOWN, width=7.6).move_to([-2.7, -0.9, 0])
        bar = self.line_bar(code, 1, color=ACCENT).set_fill(opacity=0.35)
        ring = SurroundingRectangle(VGroup(code.code_lines[1], code.code_lines[3]), color="#FF4D4D", buff=0.12,
                                    stroke_width=10, corner_radius=0.15)
        self.add(self.shadow(code.background), code, bar, ring)
        title = headline_text("DON'T DELETE THIS!", 92, ACCENT).to_edge(UP, buff=0.5)
        bit = self.shocked_bit(1.6).move_to([4.6, -1.3, 0])
        bit.pose_arms(95, Bit.REST)  # pointing at the circled lines
        self.add(title, bit)


class ThumbnailStack(Thumbnail):
    """STACK OVERFLOW: a toppling red call stack and a knocked-out Bit."""

    def design(self):
        stack = VGroup(*[self.stack_frame(-i, RED_C if i > 2 else FRAME_COLORS[i]) for i in range(9)])
        stack.arrange(UP, buff=0.08).scale(0.75).rotate(-12 * DEGREES).move_to([5.0, 0.6, 0])
        bit = Bit().scale(1.25)
        for knocked_out in (bit.x_eyes(), bit.set_mouth("open")):
            knocked_out.begin()
            knocked_out.finish()
        bit.rotate(-PI / 2).move_to([3.0, -2.55, 0])
        words = VGroup(headline_text("STACK", 150, ACCENT), headline_text("OVERFLOW!", 115, "#FF4D4D"))
        words.arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UL, buff=0.6).shift(DOWN * 0.6)
        sub = headline_text("forgot the base case", 56, TEXT_LIGHT).next_to(words, DOWN, buff=0.4, aligned_edge=LEFT)
        self.add(stack, bit, words, sub)
