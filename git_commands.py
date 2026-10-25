"""10 git commands: init, clone, status, add, commit, log, branch, switch, merge, push.

Every command is typed in a terminal, prints what git really prints, and moves things in a
diagram of the four places git keeps your work: working directory, staging area, repository
and the remote (GitHub). The 16:9 video adds a tip per command; the Short is rapid-fire.

Render:  .venv/bin/manim -qh --fps 60 git_commands.py GitCommands
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 60 git_commands.py GitCommands
Thumbnail: .venv/bin/manim -s -r 1280,720 git_commands.py Thumbnail
"""

from bitbybit import *

ZONE_FILL, ZONE_EDGE = "#20244F", "#3A3F75"
MAIN_COLOR, FEATURE_COLOR = "#80DEEA", "#FFAB91"
TERM_AT, TERM_SIZE, TERM_FONT = pick([-3.6, 1.75, 0], [0, 4.15, 0]), pick((6.6, 3.1), (7.6, 2.5)), pick(22, 21)
BIT_AT = pick([3.3, 0.75, 0], [-2.4, -5.6, 0])  # 9:16: bubbles clear the repository
# The four places: working directory, staging area, repository, remote.
WORK_AT, STAGE_AT = pick([-5.35, -2.2, 0], [-1.95, 0.35, 0]), pick([-2.3, -2.2, 0], [1.95, 0.35, 0])
REPO_AT, REMOTE_AT = pick([1.35, -2.2, 0], [0, -2.05, 0]), pick([5.3, -2.2, 0], [0, 2.2, 0])
SMALL_ZONE, REPO_ZONE = pick((2.8, 3.1), (3.7, 1.8)), pick((4.0, 3.1), (7.7, 2.3))
MAIN_Y = REPO_AT[1] - pick(0.45, 0.4)
FEATURE_Y = MAIN_Y + pick(0.8, 0.75)
COMMIT_X = [REPO_AT[0] + dx for dx in pick([-1.45, -0.7, 0.05, 0.65, 1.3], [-2.9, -1.8, -0.7, 0.4, 1.5])]
HASHES = ["9e8d7c6", "a1b2c3d", "3f9c2e1", "c4d5e6f", "8b7a6f5"]


class GitCommands(BitScene):
    # ---------------------------------------------------------------- pieces
    def line(self, bit, text, **kwargs):
        """Bit's lines: above him on 16:9; up and to the right on 9:16, below the diagram."""
        return self.say(bit, text, pick(UP, UR), font_size=pick(32, 32), **kwargs)

    def tip(self, bit, text, **kwargs):
        """Extra advice that only the long video has time for."""
        if not SHORT:
            self.line(bit, text, **kwargs)

    def echo(self, text, color=TEXT_MUTED, run_time=0.15, short=False):
        """Terminal output; the Short only shows the lines marked short=True."""
        if not SHORT or short:
            self.term_echo(self.term, text, color=color, run_time=run_time)

    def zone(self, label, size, at):
        box = RoundedRectangle(width=size[0], height=size[1], corner_radius=0.2, fill_color=ZONE_FILL, fill_opacity=1,
                               stroke_color=ZONE_EDGE, stroke_width=3)
        text = Text(label, font=FONT, weight=BOLD, font_size=20, color=TEXT_MUTED)
        text.next_to(box.get_corner(UL), DR, buff=0.12)
        return VGroup(box, text).move_to(at)

    def cloud(self):
        puffs = VGroup(*[Circle(radius=r, fill_color="#2E3577", fill_opacity=1, stroke_width=0).move_to([x, y, 0])
                         for x, y, r in ((-0.75, -0.1, 0.45), (-0.15, 0.2, 0.6), (0.6, 0.05, 0.5), (1.05, -0.2, 0.32))])
        base = RoundedRectangle(width=2.4, height=0.55, corner_radius=0.27, fill_color="#2E3577", fill_opacity=1,
                                stroke_width=0).move_to([0.1, -0.35, 0])
        label = Text("GitHub", font=FONT, weight=BOLD, font_size=20, color=TEXT_MUTED).move_to([0.1, 0.42, 0])
        dots = VGroup()  # the remote's commits
        cloud = VGroup(puffs, base, label).scale(pick(1.0, 0.9)).move_to(REMOTE_AT)
        cloud.dots = dots
        return cloud

    def remote_dot(self, cloud, k):
        return Dot(radius=0.09, color=ACCENT).move_to(cloud[1].get_center() + RIGHT * (k - 2) * 0.32)

    def file_card(self, name, color=FRAME_COLORS[0]):
        box = RoundedRectangle(width=1.75, height=0.42, corner_radius=0.08, fill_color=color, fill_opacity=1,
                               stroke_color=INK, stroke_width=3)
        return VGroup(box, Text(name, font=MONO, weight=BOLD, font_size=20, color=INK).move_to(box))

    def commit(self, k, y=None):
        dot = Circle(radius=0.17, fill_color=ACCENT, fill_opacity=1, stroke_color=INK, stroke_width=3)
        dot.move_to([COMMIT_X[k], MAIN_Y if y is None else y, 0])
        label = Text(HASHES[k][:4], font=MONO, font_size=15, color=TEXT_MUTED).next_to(dot, DOWN, buff=0.06)
        return VGroup(dot, label)

    def link(self, a, b, color=MAIN_COLOR):
        return Line(a[0].get_center(), b[0].get_center(), stroke_color=color, stroke_width=5, buff=0.17)

    def pill(self, name, color):
        text = Text(name, font=MONO, weight=BOLD, font_size=18, color=INK)
        box = RoundedRectangle(width=text.width + 0.3, height=0.34, corner_radius=0.17, fill_color=color,
                               fill_opacity=1, stroke_color=INK, stroke_width=2)
        return VGroup(box, text.move_to(box))

    def head_ring(self, pill):
        return SurroundingRectangle(pill, color=ACCENT, buff=0.06, corner_radius=0.2, stroke_width=4)

    def step(self, n, command, summary):
        """Start command n: chapter, terminal title, a cleared screen."""
        self.chapter(f"cmd{n}", f"{n}. git {command}: {summary}")
        title = Text(f"{n}/10 · git {command}", font=MONO, weight=BOLD, font_size=22, color=ACCENT)
        self.term_clear(self.term)
        self.sfx("pop", gain=-4)
        self.play(Transform(self.term[4], title.move_to(self.term[4])), run_time=0.25)

    def hook_visual(self):
        """A terminal full of git and a confident Bit."""
        term = self.terminal(7.4, 3.0, font_size=30).move_to(UP * 0.9)
        lines = VGroup(*[Text(t, font=MONO, font_size=30, color=c) for t, c in (
            ("$ git add .", TEXT_LIGHT), ("$ git commit -m \"wow\"", TEXT_LIGHT), ("$ git push", TEXT_LIGHT),
            ("  main -> main", CONSOLE_GREEN))])
        lines.arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to(term[1]).shift(DOWN * 0.15)
        for l in lines[:3]:
            l[0].set_color(CONSOLE_GREEN)
        burst = sunburst(512, round=True).set(height=5.2).move_to(DOWN * 3.1)
        ten = headline_text("10", 150, ACCENT).move_to([2.4, -1.6, 0])
        bit = Bit().scale(1.05).move_to(DOWN * 3.5)
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("smug"))
        return Group(burst, term, lines, ten, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "10 git commands")
            self.hook_open(("Know these 10 git commands?", "You'll use them DAILY."),
                           "Ten git commands you'll use every single day. Ready?", sound="ding", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.graph_title()
        bit = self.workspace(bit, title)
        self.init_(bit)
        self.clone(bit)
        self.status(bit)
        self.add_(bit)
        self.commit_(bit)
        self.log_(bit)
        self.branch(bit)
        self.switch(bit)
        self.merge(bit)
        self.push(bit)
        if not SHORT:
            bit = Bit().scale(0.5).move_to([-6.2, -2.9, 0])
            self.play(FadeIn(bit, shift=UP * 0.5), run_time=0.3)
            self.cheat_sheet(bit, '10 GIT COMMANDS', [('git init', 'start a repository'), ('git clone <url>', 'copy a project'), ('git status', 'what changed?'), ('git add <file>', 'stage changes'), ('git commit -m "msg"', 'save a snapshot'), ('git log --oneline', 'see the history'), ('git branch <name>', 'new line of work'), ('git switch <name>', 'move to a branch'), ('git merge <name>', 'combine branches'), ('git push / git pull', 'upload / download')])
        self.chapter("joke", "The git joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["status, add, commit, push. Repeat!"], ["status, add,", "commit, push!"]),
                    "git commit to this channel:\nsubscribe!",
                    loop_line="So... which 10 commands\nwere they again?", loop_finale=self.hook_look)

    def graph_title(self):
        """The opening: a commit graph draws itself (commit, branch off, merge back), then the title."""
        y = pick(0.2, 1.4)
        xs = [-3.6, -2.2, -0.8, 0.6, 2.0, 3.4] if not VERTICAL else [-3.0, -1.8, -0.6, 0.6, 1.8, 3.0]
        main = [Circle(radius=0.24, fill_color=ACCENT, fill_opacity=1, stroke_color=INK, stroke_width=4).move_to([x, y, 0])
                for x in (xs[0], xs[1], xs[2], xs[5])]
        side = [Circle(radius=0.24, fill_color=FEATURE_COLOR, fill_opacity=1, stroke_color=INK, stroke_width=4)
                .move_to([x, y + 0.9, 0]) for x in (xs[3], xs[4])]
        bit = Bit().scale(0.8).move_to(DOWN * pick(2.2, 2.6))
        self.sfx("boing")
        self.play(FadeIn(bit, shift=UP * 2.0), run_time=0.45, rate_func=rate_functions.ease_out_back)
        self.play(bit.look(UP), run_time=0.15)
        drawn = VGroup()
        for a, b in [(None, main[0]), (main[0], main[1]), (main[1], main[2]), (main[2], side[0]), (side[0], side[1]),
                     (side[1], main[3]), (main[2], main[3])]:
            anims = [FadeIn(b, scale=0.4)] if b not in drawn else []
            if a is not None:
                edge = Line(a.get_center(), b.get_center(), buff=0.24, stroke_width=6,
                            stroke_color=FEATURE_COLOR if b in side or a in side else MAIN_COLOR)
                anims.insert(0, Create(edge))
                drawn.add(edge)
            drawn.add(b)
            self.sfx("pop", gain=-4)
            self.play(*anims, run_time=0.2)
        title = headline_text("10 GIT COMMANDS", pick(96, 70), HEADLINE).move_to([0, y + 2.0, 0])
        title.scale_to_fit_width(min(title.width, config.frame_width - 0.8))
        self.sfx("ding")
        self.play(FadeIn(title, scale=1.3), drawn.animate(rate_func=there_and_back).scale(1.05),
                  bit.look(ORIGIN), bit.express("grin", "smug"), run_time=0.4)
        self.moment("topic")
        spoken = self.voice("Ten git commands.", captioned=True)
        self.play(bit.talk(max(spoken, 0.5)))
        self.play(bit.express("smile", "neutral"), run_time=0.15)
        return bit, VGroup(title, drawn)

    def workspace(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: the 10 git commands\nyou'll use EVERY day.", UR, gesture=bit.point(0, 165))
            self.say(bit, "One project, start to finish.\nLet's go!", UR)
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.6 / 0.8).move_to(BIT_AT), run_time=0.4)
        self.term = self.terminal(*TERM_SIZE, title="bash", font_size=TERM_FONT).move_to(TERM_AT)
        self.work = self.zone("Working dir", SMALL_ZONE, WORK_AT)
        self.stage_zone = self.zone("Staging", SMALL_ZONE, STAGE_AT)
        self.repo = self.zone("Repository", REPO_ZONE, REPO_AT)
        self.remote = self.cloud()
        self.files = VGroup(self.file_card("app.py"), self.file_card("README.md", FRAME_COLORS[2]))
        self.files.arrange(DOWN, buff=0.12).move_to(self.work[0]).shift(DOWN * 0.15)
        self.sfx("whoosh", gain=-4)
        self.play(FadeIn(self.term, shift=DOWN * 0.3), FadeIn(self.work), FadeIn(self.files), run_time=0.5)
        return bit

    # ------------------------------------------------------------ commands
    def init_(self, bit):
        self.step(1, "init", "start a repository")
        self.term_type(self.term, "git init")
        self.echo("Initialized empty Git repository", run_time=0.2)
        self.sfx("pop")
        self.play(FadeIn(self.repo, scale=0.9), FadeIn(self.stage_zone, scale=0.9), run_time=0.4)
        self.line(bit, pick("init turns a folder into\na Git repository.", "init: Git starts tracking\nthis folder."))
        self.tip(bit, "Run it once, in a\nbrand-new project folder.")

    def clone(self, bit):
        self.step(2, "clone", "copy a project")
        self.tip(bit, "Joining a project instead?\nUse clone.")
        self.sfx("pop")
        self.remote.dots.add(*[self.remote_dot(self.remote, k) for k in range(2)])
        self.play(FadeIn(self.remote, scale=0.8), FadeIn(self.remote.dots), run_time=0.4)
        self.term_type(self.term, "git clone git@github.com:bit/app")
        self.echo("Cloning into 'app'... done.")
        self.commits = [self.commit(0), self.commit(1)]
        edge = self.link(*self.commits)
        self.sfx("whoosh")
        self.play(*[TransformFromCopy(self.remote.dots[k], self.commits[k], path_arc=PI / 4) for k in range(2)],
                  run_time=0.6)
        self.play(Create(edge), run_time=0.2)
        self.edges = VGroup(edge)
        self.main_pill = self.pill("main", MAIN_COLOR).next_to(self.commits[1][0], DOWN, buff=0.35)
        self.head = self.head_ring(self.main_pill)
        self.play(FadeIn(self.main_pill, shift=UP * 0.2), Create(self.head), run_time=0.3)
        self.line(bit, pick("clone downloads the project\nAND its whole history.", "clone: download a project\nand its history."))

    def status(self, bit):
        self.step(3, "status", "what changed?")
        card = self.files[0]
        mark = Text("M", font=MONO, weight=BOLD, font_size=22, color="#FF6B6B").next_to(card, LEFT, buff=0.08)
        self.sfx("key")
        self.play(Wiggle(card), FadeIn(mark, scale=1.5), run_time=0.5)
        self.term_type(self.term, "git status")
        self.echo("On branch main")
        self.echo("modified:   app.py", color="#FF6B6B", short=True)
        self.line(bit, pick("status shows what changed.\nRun it ALL the time!", "status: what changed?"))
        self.tip(bit, "Red means changed,\nbut not staged yet.")
        self.modified = mark

    def add_(self, bit):
        self.step(4, "add", "stage changes")
        self.term_type(self.term, "git add app.py")
        staged = self.files[0].copy().set_color(CONSOLE_GREEN)
        staged[1].set_color(INK)
        self.sfx("whoosh", gain=-4)
        self.play(staged.animate.move_to(self.stage_zone[0]).shift(DOWN * 0.15), FadeOut(self.modified), run_time=0.5)
        self.staged = staged
        self.line(bit, pick("add puts changes in STAGING:\nthe box for your next commit.", "add: stage it for\nthe next commit."))
        self.tip(bit, "git add . stages\nEVERYTHING at once.", speech="git add dot stages everything at once.")

    def commit_(self, bit):
        self.step(5, "commit", "save a snapshot")
        self.term_type(self.term, 'git commit -m "Add login"')
        self.echo("[main 3f9c2e1] Add login")
        new = self.commit(2)
        edge = self.link(self.commits[1], new)
        self.sfx("pop")
        self.play(ReplacementTransform(self.staged, new), run_time=0.5)
        self.play(Create(edge), self.main_pill.animate.next_to(new[0], DOWN, buff=0.35),
                  self.head.animate.move_to(self.main_pill.copy().next_to(new[0], DOWN, buff=0.35)), run_time=0.3)
        self.commits.append(new)
        self.edges.add(edge)
        self.line(bit, pick("commit saves a snapshot\nwith a message.", "commit: save a snapshot."))
        self.tip(bit, "Write messages your\nfuture self will understand!")

    def log_(self, bit):
        self.step(6, "log", "see the history")
        self.term_type(self.term, "git log --oneline")
        for k, msg in ((2, "Add login"), (1, "Fix typo"), (0, "First commit")):
            self.echo(f"{HASHES[k]} {msg}", color=ACCENT if k == 2 else TEXT_MUTED, run_time=0.12, short=True)
            self.play(Indicate(self.commits[k], color=ACCENT, scale_factor=1.4), run_time=0.3)
        self.line(bit, pick("log lists the history,\nnewest first.", "log: see the history."))
        self.tip(bit, "Every commit has an ID.\nYou can always go back.")

    def branch(self, bit):
        self.step(7, "branch", "start a new line of work")
        self.term_type(self.term, "git branch feature")
        self.feature_pill = self.pill("feature", FEATURE_COLOR).next_to(self.commits[2][0], UP, buff=0.3)
        self.sfx("pop")
        self.play(FadeIn(self.feature_pill, scale=1.3), run_time=0.3)
        self.line(bit, pick("branch makes a new line\nof work. Safe to experiment!", "branch: a safe place\nto experiment."))

    def switch(self, bit):
        self.step(8, "switch", "move to a branch")
        self.term_type(self.term, "git switch feature")
        self.echo("Switched to branch 'feature'")
        self.sfx("whoosh", gain=-4)
        self.play(self.head.animate.become(self.head_ring(self.feature_pill)), run_time=0.35)
        self.tip(bit, "The yellow ring is HEAD:\nwhere you are right now.")
        side = self.commit(3, FEATURE_Y)
        edge = self.link(self.commits[2], side, FEATURE_COLOR)
        self.sfx("pop")
        self.play(Create(edge), FadeIn(side, scale=0.5), run_time=0.35)
        self.play(self.feature_pill.animate.next_to(side[0], UP, buff=0.12),
                  self.head.animate.move_to(self.feature_pill.copy().next_to(side[0], UP, buff=0.12)), run_time=0.3)
        self.commits.append(side)
        self.edges.add(edge)
        self.line(bit, pick("New commits now go\non the feature branch.", "switch: hop onto it."))
        self.tip(bit, "Older tutorials say\ngit checkout. Same idea.")

    def merge(self, bit):
        self.step(9, "merge", "combine branches")
        self.term_type(self.term, "git switch main")
        self.play(self.head.animate.become(self.head_ring(self.main_pill)), run_time=0.3)
        self.term_type(self.term, "git merge feature")
        self.echo("Merge made by the 'ort' strategy.")
        joined = self.commit(4)
        edges = [self.link(self.commits[2], joined), self.link(self.commits[3], joined, FEATURE_COLOR)]
        self.moment("payoff")
        self.sfx("ding")
        self.play(*[Create(e) for e in edges], FadeIn(joined, scale=0.5), run_time=0.45)
        self.play(self.main_pill.animate.next_to(joined[0], DOWN, buff=0.35),
                  self.head.animate.move_to(self.main_pill.copy().next_to(joined[0], DOWN, buff=0.35)),
                  Flash(joined[0], color=ACCENT), bit.express("grin", "raised"), run_time=0.4)
        self.commits.append(joined)
        self.edges.add(*edges)
        self.line(bit, pick("merge brings the feature's\nwork back into main.", "merge: bring it back\ninto main."))
        self.tip(bit, "Same lines edited on both?\nGit asks YOU to choose.")
        self.play(bit.express("smile", "neutral"), run_time=0.15)

    def push(self, bit):
        self.step(10, "push", "upload to GitHub")
        self.term_type(self.term, "git push")
        self.echo("main -> main", color=CONSOLE_GREEN, short=True)
        dots = [self.remote_dot(self.remote, k) for k in range(2, 5)]
        self.sfx("whoosh")
        self.play(*[TransformFromCopy(self.commits[k][0], d, path_arc=-PI / 4) for k, d in zip((2, 3, 4), dots)],
                  run_time=0.6)
        self.remote.dots.add(*dots)
        self.sfx("ding")
        self.play(Indicate(self.remote, color=ACCENT, scale_factor=1.08), run_time=0.4)
        self.line(bit, pick("push uploads your commits.\nNow your team has them!", "push: upload to GitHub."))
        if not SHORT:
            self.term_type(self.term, "git pull")
            self.echo("Already up to date.")
            self.line(bit, "And git pull downloads\nyour team's new commits.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "Why did the developer\nbreak up with git?", "Too many COMMITMENT\nissues.",
                  speech_punch="Too many commitment issues.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, GitCommands):
    def design(self):
        """10 GIT COMMANDS: a branch-and-merge graph and a confident Bit."""
        dx, y = pick((0, -2.6), (2.35, 0.2))  # 9:16: the graph centered under the title
        xs = [x + dx for x in (-5.6, -4.3, -3.0, -0.4, 0.9)]
        main = [Circle(radius=0.32, fill_color=ACCENT, fill_opacity=1, stroke_color=INK, stroke_width=5).move_to([x, y, 0])
                for x in xs]
        side = [Circle(radius=0.32, fill_color=FEATURE_COLOR, fill_opacity=1, stroke_color=INK, stroke_width=5)
                .move_to([x + dx, y + 1.2, 0]) for x in (-1.9,)]
        edges = VGroup(*[Line(a.get_center(), b.get_center(), buff=0.32, stroke_width=9, stroke_color=MAIN_COLOR)
                         for a, b in zip(main, main[1:])],
                       Line(main[2].get_center(), side[0].get_center(), buff=0.32, stroke_width=9, stroke_color=FEATURE_COLOR),
                       Line(side[0].get_center(), main[3].get_center(), buff=0.32, stroke_width=9, stroke_color=FEATURE_COLOR))
        words = VGroup(headline_text("10 GIT", 150, ACCENT), headline_text("COMMANDS", 110, TEXT_LIGHT))
        if VERTICAL:  # Reels/Shorts cover: centered, clear of the cropped top and bottom
            words.arrange(DOWN, buff=0.05).scale_to_fit_width(7.2).move_to(UP * 4.8)
        else:
            words.arrange(DOWN, aligned_edge=LEFT, buff=0.05).to_corner(UL, buff=0.5)
        sub = headline_text("you'll use EVERY day", 54, HEADLINE)
        sub.next_to(words, DOWN, buff=0.25, aligned_edge=pick(LEFT, ORIGIN))
        bit = Bit().scale(1.5).move_to(pick([4.6, -1.0, 0], [0, -2.7, 0]))
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("smug"))
        bit.pose_arms(150, Bit.REST)
        self.add(edges, *main, *side, words, sub, bit)
