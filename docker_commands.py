"""10 Docker commands: pull, images, run, ps, logs, exec, stop, rm, build, compose up.

Each command is typed in a terminal, prints what Docker prints, and moves things in a diagram:
the registry (Docker Hub), the images on your machine and the containers running from them.
The key idea, said early and kept as the takeaway: an image is the recipe, a container the cake.

Render:  .venv/bin/manim -qh --fps 30 docker_commands.py DockerCommands
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 docker_commands.py DockerCommands
Thumbnail: .venv/bin/manim -s -r 1280,720 docker_commands.py Thumbnail
"""

from bitbybit import *

ZONE_FILL, ZONE_EDGE = "#20244F", "#3A3F75"
DOCKER_BLUE, RUNNING, STOPPED = "#2496ED", "#43A047", "#E53935"
TERM_AT, TERM_SIZE, TERM_FONT = pick([-3.6, 1.75, 0], [0, 4.15, 0]), pick((6.6, 3.1), (7.6, 2.5)), pick(22, 21)
BIT_AT = pick([3.3, 0.75, 0], [-2.4, -5.6, 0])
HUB_AT = pick([-5.3, -2.2, 0], [0, 2.2, 0])
IMAGES_AT, IMAGES_SIZE = pick([-1.85, -2.2, 0], [0, 0.35, 0]), pick((3.2, 3.1), (7.7, 1.8))
BOX_AT, BOX_SIZE = pick([3.3, -2.2, 0], [0, -2.05, 0]), pick((6.6, 3.1), (7.7, 2.3))  # the containers
CID = "f3a1c9e2b7d4"


class DockerCommands(BitScene):
    # ---------------------------------------------------------------- pieces
    def line(self, bit, text, **kwargs):
        """Bit's lines: above him on 16:9; up and to the right on 9:16, below the diagram."""
        return self.say(bit, text, pick(UP, UR), **kwargs)

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
        text = Text(label, font=FONT, weight=BOLD, font_size=20, color=TEXT_MUTED).next_to(box.get_corner(UL), DR, buff=0.12)
        return VGroup(box, text).move_to(at)

    def hub(self):
        puffs = VGroup(*[Circle(radius=r, fill_color="#1D4E89", fill_opacity=1, stroke_width=0).move_to([x, y, 0])
                         for x, y, r in ((-0.75, -0.1, 0.45), (-0.15, 0.2, 0.6), (0.6, 0.05, 0.5), (1.05, -0.2, 0.32))])
        base = RoundedRectangle(width=2.4, height=0.55, corner_radius=0.27, fill_color="#1D4E89", fill_opacity=1,
                                stroke_width=0).move_to([0.1, -0.35, 0])
        label = Text("Docker Hub", font=FONT, weight=BOLD, font_size=20, color=TEXT_LIGHT).move_to([0.1, 0.42, 0])
        return VGroup(puffs, base, label).scale(pick(1.0, 0.9)).move_to(HUB_AT)

    def image(self, name, color=DOCKER_BLUE):
        """An image: a stack of layers with its name."""
        layers = VGroup(*[RoundedRectangle(width=1.3, height=0.16, corner_radius=0.05, stroke_width=2, stroke_color=INK,
                                           fill_color=interpolate_color(ManimColor(color), ManimColor(WHITE), 0.15 * k),
                                           fill_opacity=1) for k in range(3)]).arrange(UP, buff=0.04)
        label = Text(name, font=MONO, weight=BOLD, font_size=20, color=TEXT_LIGHT).next_to(layers, DOWN, buff=0.08)
        return VGroup(layers, label)

    def container(self, name, image_name):
        """A running container: a shipping box with ribs, a status light and its names."""
        box = RoundedRectangle(width=1.7, height=1.0, corner_radius=0.08, fill_color="#00838F", fill_opacity=1,
                               stroke_color=INK, stroke_width=4)
        ribs = VGroup(*[Line(box.get_top() + DOWN * 0.12 + RIGHT * x, box.get_bottom() + UP * 0.12 + RIGHT * x,
                             stroke_color="#006064", stroke_width=4) for x in (-0.5, -0.25, 0, 0.25, 0.5)])
        light = Dot(radius=0.09, color=RUNNING).move_to(box.get_corner(UR) + np.array([-0.18, -0.18, 0]))
        label = Text(name, font=MONO, weight=BOLD, font_size=20, color=WHITE).move_to(box)
        label.set_stroke(INK, 4, background=True)
        sub = Text(image_name, font=MONO, font_size=16, color=TEXT_MUTED).next_to(box, DOWN, buff=0.08)
        return VGroup(box, ribs, light, label, sub)

    def dockerfile(self):
        page = RoundedRectangle(width=2.3, height=1.15, corner_radius=0.06, fill_color="#ECEFF1", fill_opacity=1,
                                stroke_color=INK, stroke_width=3)
        lines = VGroup(*[Text(t, font=MONO, font_size=15, color=INK) for t in
                         ("FROM python:3.12", "COPY . /app", 'CMD ["python", "app.py"]')]).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        title = Text("Dockerfile", font=MONO, weight=BOLD, font_size=16, color="#1D6FA3")
        body = VGroup(title, lines).arrange(DOWN, aligned_edge=LEFT, buff=0.08).move_to(page)
        return VGroup(page, body)

    def step(self, n, command, summary):
        self.chapter(f"cmd{n}", f"{n}. docker {command}: {summary}")
        title = Text(f"{n}/10 · docker {command}", font=MONO, weight=BOLD, font_size=22, color=ACCENT)
        self.term_clear(self.term)
        self.sfx("pop", gain=-4)
        self.play(Transform(self.term[4], title.move_to(self.term[4])), run_time=0.25)

    def screen(self, ok):
        """A monitor with a big check (it works) or cross (it doesn't)."""
        frame = RoundedRectangle(width=2.9, height=2.0, corner_radius=0.15, fill_color="#11111B", fill_opacity=1,
                                 stroke_color="#90A4AE", stroke_width=6)
        stand = VGroup(Rectangle(width=0.3, height=0.35, fill_color="#90A4AE", fill_opacity=1, stroke_width=0),
                       RoundedRectangle(width=1.2, height=0.14, corner_radius=0.06, fill_color="#90A4AE", fill_opacity=1,
                                        stroke_width=0)).arrange(DOWN, buff=0).next_to(frame, DOWN, buff=0)
        if ok:
            mark = VMobject().set_points_as_corners([[-0.45, 0, 0], [-0.12, -0.35, 0], [0.5, 0.35, 0]]).set_stroke(RUNNING, 16)
        else:
            mark = VGroup(Line(UL * 0.4, DR * 0.4), Line(UR * 0.4, DL * 0.4)).set_stroke(STOPPED, 16)
        caption = Text("my machine" if ok else "the server", font=FONT, weight=BOLD, font_size=24, color=TEXT_LIGHT)
        caption.next_to(stand, DOWN, buff=0.12)
        return VGroup(frame, stand, mark.move_to(frame), caption)

    def hook_visual(self):
        """"It works on my machine!" - but not on the server."""
        glow = Rectangle(width=config.frame_width + 2, height=config.frame_height + 2, stroke_width=0,
                         fill_color=RED, fill_opacity=0.16)
        screens = VGroup(self.screen(True), self.screen(False)).arrange(RIGHT, buff=0.6).move_to(UP * 0.6)
        bit = self.shocked_bit(1.2).move_to(DOWN * 3.2)
        return Group(glow, screens, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "It works on my machine")
            self.hook_open(('"It works on MY machine!"', "Docker fixes that."),
                           "It works on my machine! ... Docker fixes that.", sound="oops", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.container_title()
        bit = self.workspace(bit, title)
        self.pull(bit)
        self.images(bit)
        self.run_(bit)
        self.ps(bit)
        self.logs(bit)
        self.exec_(bit)
        self.stop(bit)
        self.rm(bit)
        self.build(bit)
        self.compose(bit)
        if not SHORT:
            bit = Bit().scale(0.5).move_to([-6.2, -2.9, 0])
            self.play(FadeIn(bit, shift=UP * 0.5), run_time=0.3)
            self.cheat_sheet(bit, '10 DOCKER COMMANDS', [('docker pull <image>', 'download an image'), ('docker images', 'list your images'), ('docker run <image>', 'start a container'), ('docker ps', 'list running containers'), ('docker logs <id>', 'see what it printed'), ('docker exec -it <id> bash', 'a shell inside'), ('docker stop <id>', 'stop a container'), ('docker rm <id>', 'delete a container'), ('docker build -t <name> .', 'build an image'), ('docker compose up', 'start the whole app')])
        self.chapter("joke", "The Docker joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["Image = recipe. Container = cake."], ["Image = recipe,", "container = cake."]),
                    "Subscribe once. It works\non EVERY machine!",
                    loop_line="Wait... does it work\non YOUR machine?", loop_finale=self.hook_look)

    def container_title(self):
        """The opening: a shipping container slides in, its doors swing open, the title is inside."""
        w, h = pick((8.6, 3.2), (7.4, 3.6))
        box = RoundedRectangle(width=w, height=h, corner_radius=0.12, fill_color="#0E1020", fill_opacity=1,
                               stroke_color=INK, stroke_width=6).move_to(UP * pick(0.9, 2.0))
        lines = pick(["10 DOCKER", "COMMANDS"], ["10 DOCKER", "COMMANDS"])
        title = VGroup(*[headline_text(l, pick(96, 80), DOCKER_BLUE if k == 0 else HEADLINE) for k, l in enumerate(lines)])
        title.arrange(DOWN, buff=0.1).move_to(box)
        title.scale_to_fit_width(min(title.width, w - 0.6))
        doors = VGroup()
        for side in (-1, 1):
            door = Rectangle(width=w / 2, height=h, fill_color="#00838F", fill_opacity=1, stroke_color=INK, stroke_width=5)
            door.move_to(box.get_center() + RIGHT * side * w / 4)
            ribs = VGroup(*[Line(door.get_top() + DOWN * 0.15 + RIGHT * x, door.get_bottom() + UP * 0.15 + RIGHT * x,
                                 stroke_color="#006064", stroke_width=6)
                            for x in np.linspace(-w / 4 + 0.35, w / 4 - 0.35, 5)])
            handle = Line(UP * 0.5, DOWN * 0.5, stroke_color="#B0BEC5", stroke_width=8).move_to(
                door.get_center() - RIGHT * side * (w / 4 - 0.25))
            doors.add(VGroup(door, ribs, handle))
        crate = VGroup(box, title, doors)
        bit = Bit().scale(0.8).move_to(box.get_center() + DOWN * 0.1)
        crate.shift(RIGHT * config.frame_width)
        self.sfx("whoosh")
        self.play(crate.animate.shift(LEFT * config.frame_width), run_time=0.6, rate_func=rate_functions.ease_out_cubic)
        self.sfx("boing")
        self.play(crate.animate(rate_func=there_and_back).shift(DOWN * 0.12), run_time=0.25)
        self.sfx("slide_down", gain=-6)
        self.play(doors[0].animate.stretch(0.05, 0, about_edge=LEFT), doors[1].animate.stretch(0.05, 0, about_edge=RIGHT),
                  run_time=0.5)
        self.moment("topic")
        self.sfx("ding")
        self.play(title.animate(rate_func=there_and_back).scale(1.06), run_time=0.3)
        spoken = self.voice("Ten Docker commands.", captioned=True)
        self.wait(max(spoken, 0.5))
        # Bit hops out of the container.
        bit.move_to(box.get_bottom() + DOWN * pick(1.4, 1.7))
        self.sfx("boing")
        self.play(FadeIn(bit, shift=UP * 0.8), run_time=0.35, rate_func=rate_functions.ease_out_back)
        return bit, crate

    def workspace(self, bit, crate):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: the 10 Docker commands\nyou actually need. Let's go!", UR, gesture=bit.point(0, 165))
        self.sfx("whoosh")
        self.play(FadeOut(crate, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.6 / 0.8).move_to(BIT_AT), run_time=0.4)
        self.term = self.terminal(*TERM_SIZE, title="bash", font_size=TERM_FONT).move_to(TERM_AT)
        self.hub_cloud = self.hub()
        self.images_zone = self.zone("Images", IMAGES_SIZE, IMAGES_AT)
        self.boxes_zone = self.zone("Containers", BOX_SIZE, BOX_AT)
        self.sfx("whoosh", gain=-4)
        self.play(FadeIn(self.term, shift=DOWN * 0.3), FadeIn(self.hub_cloud), FadeIn(self.images_zone),
                  FadeIn(self.boxes_zone), run_time=0.5)
        return bit

    def image_spot(self, k):
        """Where the k-th image sits in the images zone."""
        zone = self.images_zone[0]
        return zone.get_center() + pick(DOWN * 0.1 + UP * (0.7 - 1.1 * k), RIGHT * (-1.9 + 2.0 * k) + DOWN * 0.1)

    def box_spot(self, k):
        zone = self.boxes_zone[0]
        return zone.get_center() + RIGHT * (-2.0 + 2.1 * k) * pick(0.95, 1.0) + DOWN * 0.05

    # ------------------------------------------------------------ commands
    def pull(self, bit):
        self.step(1, "pull", "download an image")
        self.term_type(self.term, "docker pull nginx")
        self.echo("Pulling from library/nginx")
        self.nginx = self.image("nginx").move_to(self.hub_cloud)
        self.play(FadeIn(self.nginx, scale=0.5), run_time=0.25)
        self.sfx("whoosh")
        self.play(self.nginx.animate(path_arc=-PI / 4).move_to(self.image_spot(0)), run_time=0.5)
        self.echo("Downloaded nginx:latest", color=CONSOLE_GREEN)
        self.line(bit, pick("pull downloads an IMAGE:\na ready-to-run app package.", "pull: download an image."))
        self.tip(bit, "Images live on Docker Hub,\nlike apps in an app store.")

    def images(self, bit):
        self.step(2, "images", "list your images")
        self.term_type(self.term, "docker images")
        self.echo("REPOSITORY  TAG     SIZE", color=TEXT_LIGHT)
        self.echo("nginx       latest  188MB", short=True)
        self.play(Indicate(self.nginx, color=ACCENT, scale_factor=1.15), run_time=0.4)
        self.line(bit, pick("images lists the images\non your machine.", "images: list your images."))

    def run_(self, bit):
        self.step(3, "run", "start a container")
        self.term_type(self.term, "docker run -d -p 8080:80 nginx")
        self.echo(CID, color=CONSOLE_GREEN)
        self.web = self.container("web", "nginx").move_to(self.box_spot(0))
        self.sfx("pop")
        self.play(TransformFromCopy(self.nginx, self.web, path_arc=-PI / 3), run_time=0.6)
        self.play(Flash(self.web[2], color=RUNNING, flash_radius=0.3), run_time=0.3)
        self.line(bit, pick("run starts a CONTAINER: a\nrunning copy of an image.", "run: start a container\nfrom an image."))
        self.moment("reveal")
        self.line(bit, "Image = the recipe.\nContainer = the cake!")
        self.tip(bit, "-d runs it in the background.\n-p 8080:80 opens a port.",
                 speech="Dash d runs it in the background. Dash p eighty-eighty to eighty opens a port.")

    def ps(self, bit):
        self.step(4, "ps", "list running containers")
        self.term_type(self.term, "docker ps")
        self.echo("CONTAINER ID  IMAGE  STATUS", color=TEXT_LIGHT)
        self.echo(f"{CID}  nginx  Up 5 seconds", short=True)
        self.play(Indicate(self.web, color=ACCENT, scale_factor=1.1), run_time=0.4)
        self.line(bit, pick("ps lists the containers\nthat are RUNNING.", "ps: what's running?"))
        self.tip(bit, "Add -a to see the\nstopped ones too.", speech="Add dash a to see the stopped ones too.")

    def logs(self, bit):
        self.step(5, "logs", "see what the app printed")
        self.term_type(self.term, f"docker logs {CID[:4]}")
        for text in ('"GET / HTTP/1.1" 200', '"GET /about HTTP/1.1" 200'):
            note = Text("log", font=MONO, font_size=18, color=ACCENT).move_to(self.web[0])
            self.play(note.animate.move_to(self.term[1].get_center()).set_opacity(0), run_time=0.3)
            self.remove(note)
            self.echo(text, short=True)
        self.line(bit, pick("logs shows what the app\ninside has printed.", "logs: what did it print?"))
        self.tip(bit, "Add -f to follow\nthe logs live.", speech="Add dash f to follow the logs live.")

    def exec_(self, bit):
        self.step(6, "exec", "run a command inside")
        self.term_type(self.term, f"docker exec -it {CID[:4]} bash")
        self.echo(f"root@{CID[:4]}:/#", color=CONSOLE_GREEN, short=True)
        # Bit dives into the container...
        home = bit.get_center()
        self.moment("gag")
        self.sfx("slide_down", gain=-4)
        self.play(bit.animate(path_arc=-PI / 2).scale(0.3).move_to(self.web[0]), run_time=0.5)
        self.play(Wiggle(self.web, scale_value=1.15), run_time=0.5)
        shout = Text("I'm inside!", font=FONT, weight=BOLD, font_size=28, color=ACCENT)
        shout.set_stroke(INK, 5, background=True).next_to(self.web, UP, buff=0.1)
        self.play(FadeIn(shout, scale=1.3), run_time=0.2)
        voice = self.voice("I'm inside!", captioned=True)
        self.log("text", "I'm inside!", max(voice, 1.0) + 0.35, words=2)
        self.wait(max(voice, 1.0))
        self.play(FadeOut(shout), run_time=0.15)
        # ...and back out.
        self.sfx("boing")
        self.play(bit.animate(path_arc=PI / 2).scale(1 / 0.3).move_to(home), run_time=0.5)
        self.line(bit, pick("exec runs a command INSIDE\na running container.", "exec: run commands inside."))
        self.tip(bit, "-it gives you an interactive\nshell. Type exit to leave.",
                 speech="Dash i t gives you an interactive shell. Type exit to leave.")

    def stop(self, bit):
        self.step(7, "stop", "stop a container")
        self.term_type(self.term, f"docker stop {CID[:4]}")
        self.echo(CID[:4])
        self.sfx("oops")
        self.play(self.web[2].animate.set_color(STOPPED), self.web[0].animate.set_fill("#455A64"), run_time=0.4)
        self.line(bit, pick("stop shuts the container\ndown. Gently.", "stop: shut it down."))
        self.tip(bit, "It's not deleted:\ndocker start brings it back.")

    def rm(self, bit):
        self.step(8, "rm", "delete a container")
        self.term_type(self.term, f"docker rm {CID[:4]}")
        self.echo(CID[:4])
        self.sfx("crash")
        self.play(FadeOut(self.web, scale=0.3, shift=DOWN * 0.3), run_time=0.4)
        self.line(bit, pick("rm deletes a stopped\ncontainer for good.", "rm: delete it."))
        self.tip(bit, "The image stays. Delete\nimages with docker rmi.")

    def build(self, bit):
        self.step(9, "build", "make your own image")
        doc = self.dockerfile().move_to(self.box_spot(0) + pick(RIGHT * 0.6, ORIGIN))
        self.sfx("pop")
        self.play(FadeIn(doc, shift=UP * 0.3), run_time=0.35)
        self.term_type(self.term, "docker build -t myapp .")
        mine = self.image("myapp", "#7E57C2").move_to(self.image_spot(1))
        self.sfx("whoosh")
        self.play(TransformFromCopy(doc, mine, path_arc=PI / 4), run_time=0.6)
        self.echo("=> naming to myapp:latest", color=CONSOLE_GREEN)
        self.line(bit, pick("build turns YOUR Dockerfile\ninto an image.", "build: your own image\nfrom a Dockerfile."))
        self.tip(bit, "Each line in the Dockerfile\nadds a layer to the image.")
        self.sfx("whoosh", gain=-6)
        self.play(FadeOut(doc), run_time=0.3)
        self.myapp = mine

    def compose(self, bit):
        self.step(10, "compose up", "start the whole app")
        self.term_type(self.term, "docker compose up -d")
        web = self.container("web", "myapp").move_to(self.box_spot(0))
        db = self.container("db", "postgres").move_to(self.box_spot(1))
        wire = DashedLine(web[0].get_right(), db[0].get_left(), color=ACCENT, stroke_width=5)
        self.sfx("pop")
        self.play(FadeIn(web, scale=0.6), run_time=0.3)
        self.echo("Container app-web-1  Started", color=CONSOLE_GREEN, short=True)
        self.sfx("pop")
        self.play(FadeIn(db, scale=0.6), Create(wire), run_time=0.35)
        self.echo("Container app-db-1   Started", color=CONSOLE_GREEN, short=True)
        self.moment("payoff")
        self.sfx("ding")
        self.play(Flash(web[2], color=RUNNING), Flash(db[2], color=RUNNING), bit.express("grin", "raised"),
                  bit.arms_up(run_time=0.3), run_time=0.45)
        self.line(bit, pick("compose up starts your WHOLE\napp: web, database, all of it.", "compose up: start\nEVERYTHING at once."))
        self.tip(bit, "It reads docker-compose.yml.\ncompose down stops it all.",
                 speech="It reads docker compose dot yml. Compose down stops it all.")
        self.play(bit.arms_rest(run_time=0.3), bit.express("smile", "neutral"), run_time=0.3)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, '"It works on my machine!"', '"Fine. Then we\'ll ship\nyour machine." That\'s Docker!',
                  speech_setup="It works on my machine!", speech_punch="Fine. Then we'll ship your machine. That's Docker!")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, DockerCommands):
    def design(self):
        """10 DOCKER COMMANDS: a stack of containers and Bit riding on top."""
        stack = VGroup()
        for row, xs in enumerate(([-1.0, 1.0, 3.0], [0.0, 2.0], [1.0])):
            for x in xs:
                stack.add(self.container("box", "box")[:3].scale(1.15)
                          .move_to([x + pick(2.6, -1.0), pick(-2.9, -3.3) + row * 1.2, 0]))
        words = VGroup(headline_text("10 DOCKER", 110, DOCKER_BLUE), headline_text("COMMANDS", 96, TEXT_LIGHT))
        if VERTICAL:  # Reels/Shorts cover: centered, clear of the cropped top and bottom
            words.arrange(DOWN, buff=0.05).scale_to_fit_width(7.2).move_to(UP * 4.6)
        else:
            words.arrange(DOWN, aligned_edge=LEFT, buff=0.05).to_corner(UL, buff=0.5)
        sub = headline_text("image = recipe, container = cake", 40, HEADLINE)
        if VERTICAL:
            sub.scale_to_fit_width(7.2)
        sub.next_to(words, DOWN, buff=0.25, aligned_edge=pick(LEFT, ORIGIN))
        bit = Bit().scale(1.0).next_to(stack, UP, buff=-0.05).shift(RIGHT * 0.0)
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("raised"))
        bit.pose_arms(150, 150)
        self.add(stack, words, sub, bit)
