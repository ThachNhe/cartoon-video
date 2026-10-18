"""Hash maps: how a Python dict finds a key in one step.

Searching a list checks names one by one. A dict runs the key through hash(), takes the
remainder by the number of buckets and goes straight to that bucket. Two keys can land in
the same bucket (a collision); the bucket keeps a short list and stays fast.

Render:  .venv/bin/manim -qh --fps 30 hash_map.py HashMap
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 hash_map.py HashMap
Thumbnail: .venv/bin/manim -s -r 1280,720 hash_map.py Thumbnail
"""

from bitbybit import *

NAMES = ["Ada", "Linus", "Grace", "Guido", "Alan", "Ken", "Bit", "Tim"]
# Illustrative hash values (Python randomizes str hashes per run); each % 8 gives the bucket.
HASHES = {"Bit": 7148, "Ada": 2652, "Grace": 9617, "Linus": 3606, "Alan": 5170}
BUCKETS = 8
PREFILLED = ["Grace", "Linus", "Alan"]  # already in the dict when Bit's key goes in
AGE = 7

# 16:9: names and buckets in rows; 9:16: in a column on the left, the machine and Bit on the right.
SLOT_W, SLOT_H = pick(1.0, 1.25), pick(0.62, 0.62)
LIST_START, LIST_STEP = pick([-6.1, 1.9, 0], [-2.55, 3.95, 0]), pick(RIGHT * 1.12, DOWN * 0.78)
BUCKET_START, BUCKET_STEP = pick([-6.1, -1.55, 0], [-2.55, 3.95, 0]), pick(RIGHT * 1.12, DOWN * 0.78)
MACHINE_AT = pick([-1.0, 1.0, 0], [1.6, 3.2, 0])
BIT_AT = pick([5.3, -2.4, 0], [1.8, -4.2, 0])  # 9:16: low, so bubbles clear the bucket column


class HashMap(BitScene):
    # ---------------------------------------------------------------- pieces
    def card(self, name, color=FRAME_COLORS[0]):
        box = RoundedRectangle(width=SLOT_W - 0.1, height=SLOT_H - 0.1, corner_radius=0.1, fill_color=color,
                               fill_opacity=1, stroke_color=INK, stroke_width=3)
        label = Text(name, font=MONO, weight=BOLD, font_size=24, color=INK)
        if label.width > box.width - 0.12:
            label.scale_to_fit_width(box.width - 0.12)
        return VGroup(box, label.move_to(box))

    def names(self):
        return VGroup(*[self.card(n, FRAME_COLORS[k % len(FRAME_COLORS)]).move_to(np.array(LIST_START) + LIST_STEP * k)
                        for k, n in enumerate(NAMES)])

    def buckets(self):
        slots = VGroup()
        for k in range(BUCKETS):
            at = np.array(BUCKET_START) + BUCKET_STEP * k
            box = RoundedRectangle(width=SLOT_W, height=SLOT_H, corner_radius=0.1, fill_color="#232756", fill_opacity=1,
                                   stroke_color="#4A50A0", stroke_width=3).move_to(at)
            index = Text(str(k), font=MONO, weight=BOLD, font_size=24, color=TEXT_MUTED)
            index.next_to(box, pick(DOWN, LEFT), buff=0.12)
            slots.add(VGroup(box, index))
        return slots

    def machine(self):
        body = RoundedRectangle(width=2.3, height=1.2, corner_radius=0.2, fill_color="#3B4175", fill_opacity=1,
                                stroke_color=INK, stroke_width=5)
        label = Text("hash()", font=MONO, weight=BOLD, font_size=40, color=ACCENT).move_to(body)
        lights = VGroup(*[Dot(radius=0.06, color=c) for c in (CONSOLE_GREEN, ACCENT, "#FF6B6B")]).arrange(RIGHT, buff=0.12)
        lights.next_to(body.get_corner(UL), DR, buff=0.12)
        return VGroup(self.shadow(body), body, label, lights).move_to(MACHINE_AT)

    def hash_card(self, name, machine, card):
        """Run `card` through the machine; returns the readout (hash, remainder) and the bucket index."""
        self.sfx("whoosh", gain=-6)
        self.play(card.animate.move_to(machine[1]).scale(0.6).set_opacity(0), run_time=0.4)
        for _ in range(3):
            self.sfx("key", gain=-2)
            self.play(machine.animate(rate_func=there_and_back).scale(1.06), run_time=0.12)
        number = HASHES[name]
        bucket = number % BUCKETS
        readout = VGroup(
            Text(f'hash("{name}") = {number}', font=MONO, weight=BOLD, font_size=28, color=TEXT_LIGHT),
            Text(f"{number} % {BUCKETS} = {bucket}", font=MONO, weight=BOLD, font_size=28, color=ACCENT),
        ).arrange(DOWN, buff=0.15, aligned_edge=LEFT).next_to(machine, pick(RIGHT, DOWN), buff=0.3)
        self.sfx("ding")
        self.play(FadeIn(readout[0], shift=pick(LEFT, UP) * 0.3), run_time=0.3)
        self.play(FadeIn(readout[1], shift=pick(LEFT, UP) * 0.3), run_time=0.3)
        return readout, bucket

    def drop(self, card, slots, bucket, offset=ORIGIN):
        target = slots[bucket][0].get_center() + offset
        self.sfx("pop")
        self.play(card.animate.set_opacity(1).scale(1 / 0.6).move_to(target), run_time=0.45)

    def hook_visual(self):
        """ages["Bit"] answered at once, and an amazed Bit."""
        code = Text('ages["Bit"]', font=MONO, weight=BOLD, font_size=64, color=TEXT_LIGHT).set_stroke(INK, 8, background=True)
        answer = headline_text("→ 7", 110, ACCENT)
        lookup = VGroup(code, answer).arrange(DOWN, buff=0.3).move_to(UP * 1.2)
        size = headline_text("in 1,000,000 keys", 40, TEXT_LIGHT).next_to(lookup, DOWN, buff=0.4)
        burst = sunburst(512, round=True).set(height=6.4).move_to(lookup)  # the channel's orange sunburst
        bit = Bit().scale(1.3).move_to(DOWN * 3.4)
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("raised"))
        bit.pose_arms(150, 150)
        return Group(burst, lookup, size, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "How does a dict find keys instantly?")
            self.hook_open(("How does Python find a key", "INSTANTLY?"), "How does Python find a key instantly?",
                           sound="ding", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.title_intro("HASH MAPS", "Hash maps.")
        self.chapter("list", "Searching a list: one by one")
        bit = self.slow(bit, title)
        self.chapter("hash", "The hash function picks a bucket")
        slots, machine = self.insert(bit)
        self.chapter("lookup", "Lookup in one step")
        self.lookup(bit, slots, machine)
        self.chapter("collision", "Collisions")
        self.collision(bit, slots, machine)
        self.chapter("joke", "The hash map joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["Fast lookups? Use a dict."], ["Fast lookups?", "Use a dict."]),
                    "Find us again in ONE step:\nsubscribe!",
                    loop_line="So how DID it find\nthe key so fast?", loop_finale=self.hook_look)

    def slow(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: how a dict finds\nany key in ONE step.", UR, gesture=bit.point(0, 165))
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.6).move_to(BIT_AT), run_time=0.4)
        cards = self.names()
        self.sfx("pop")
        self.play(LaggedStart(*[FadeIn(c, shift=pick(DOWN, RIGHT) * 0.3) for c in cards], lag_ratio=0.1), run_time=0.7)
        self.say(bit, "A list of names.\nWhere's Bit?", UP, speech="A list of names. Where's Bit?")
        arrow = Arrow(ORIGIN, pick(DOWN, LEFT) * 0.6, color=ACCENT, buff=0, stroke_width=8)
        side = pick(UP, RIGHT)
        arrow.next_to(cards[0], side, buff=0.08)
        self.play(GrowArrow(arrow), run_time=0.2)
        for k in range(NAMES.index("Bit") + 1):
            self.sfx("blip", gain=-6)
            self.play(arrow.animate.next_to(cards[k], side, buff=0.08), run_time=0.22)
        self.sfx("ding")
        self.play(Indicate(cards[NAMES.index("Bit")], color=ACCENT), run_time=0.4)
        self.moment("gag")
        self.say(bit, "7 checks. With a MILLION\nnames: a million checks.", UP,
                 speech="Seven checks. With a million names: a million checks.")
        self.sfx("whoosh")
        self.play(FadeOut(cards), FadeOut(arrow), run_time=0.4)
        return bit

    def insert(self, bit):
        slots, machine = self.buckets(), self.machine()
        self.sfx("pop")
        self.play(LaggedStart(*[FadeIn(s, scale=0.8) for s in slots], lag_ratio=0.06), FadeIn(machine, scale=0.8),
                  run_time=0.7)
        # A few keys already live in their buckets.
        early = VGroup(*[self.card(n, FRAME_COLORS[(k + 1) % 5]).move_to(slots[HASHES[n] % BUCKETS][0])
                         for k, n in enumerate(PREFILLED)])
        self.play(LaggedStart(*[FadeIn(c, scale=1.2) for c in early], lag_ratio=0.2), run_time=0.5)
        self.say(bit, "A dict has buckets.\nhash() picks the bucket.", UP, speech="A dict has buckets. Hash picks the bucket.")
        card = self.card("Bit", ACCENT).next_to(machine, pick(UP, UP), buff=0.3)
        self.play(FadeIn(card, shift=DOWN * 0.3), run_time=0.3)
        readout, bucket = self.hash_card("Bit", machine, card)
        self.moment("reveal")
        self.say(bit, "Bit becomes 7148.\nRemainder by 8: bucket 4!", UP,
                 speech="Bit becomes seven one four eight. Remainder by eight: bucket four!")
        self.drop(card, slots, bucket)
        self.play(FadeOut(readout), run_time=0.3)
        self.bit_card = card
        return slots, machine

    def lookup(self, bit, slots, machine):
        query = Text('ages["Bit"]', font=MONO, weight=BOLD, font_size=40, color=TEXT_LIGHT)
        query.next_to(machine, UP, buff=0.3)
        self.sfx("pop")
        self.play(FadeIn(query, shift=DOWN * 0.3), run_time=0.3)
        if not SHORT:
            self.say(bit, "Now look it up.\nSame key, same number.", UP)
        ghost = self.card("Bit", ACCENT).move_to(query)
        self.play(FadeOut(query), FadeIn(ghost), run_time=0.2)
        readout, bucket = self.hash_card("Bit", machine, ghost)
        jump = Arrow(readout.get_corner(pick(DL, DL)), slots[bucket][0].get_center(), color=ACCENT, buff=0.2,
                     stroke_width=8, max_tip_length_to_length_ratio=0.15)
        self.moment("payoff")
        self.sfx("whoosh")
        self.play(GrowArrow(jump), run_time=0.35)
        badge = headline_text(f"age {AGE}", 40, CONSOLE_GREEN).next_to(slots[bucket][0], pick(UP, RIGHT), buff=0.2)
        self.sfx("ding")
        self.play(Indicate(self.bit_card, color=ACCENT, scale_factor=1.3), FadeIn(badge, scale=1.4),
                  bit.express("grin", "raised"), bit.arms_up(run_time=0.3), run_time=0.5)
        self.say(bit, "Straight to bucket 4.\nONE step, not a million!", UP,
                 speech="Straight to bucket four. One step, not a million!")
        self.play(FadeOut(readout), FadeOut(jump), FadeOut(badge), FadeOut(ghost), bit.arms_rest(run_time=0.3),
                  bit.express("smile", "neutral"), run_time=0.35)

    def collision(self, bit, slots, machine):
        self.moment("twist")
        card = self.card("Ada", "#CE93D8").next_to(machine, UP, buff=0.3)
        self.play(FadeIn(card, shift=DOWN * 0.3), run_time=0.3)
        if not SHORT:
            self.say(bit, "But what if two keys\nget the SAME bucket?", UP)
        readout, bucket = self.hash_card("Ada", machine, card)
        # Ada also lands in bucket 4: the two cards share it, side by side.
        self.play(self.bit_card.animate.scale(0.62).shift(pick(LEFT, LEFT) * SLOT_W * 0.24), run_time=0.3)
        self.drop(card, slots, bucket, offset=RIGHT * SLOT_W * 0.24)
        self.play(card.animate.scale(0.62), run_time=0.2)
        self.sfx("boing")
        self.play(Indicate(slots[bucket][0], color="#FF6B6B", scale_factor=1.15), bit.express("open", "worried"), run_time=0.5)
        self.say(bit, "A COLLISION! The bucket\njust keeps a tiny list.", UP)
        self.play(bit.express("smile", "neutral"), run_time=0.2)
        if not SHORT:
            self.say(bit, "Check 2 names instead of 1.\nStill super fast.", UP,
                     speech="Check two names instead of one. Still super fast.")
        if not SHORT:
            self.say(bit, "So: need fast lookups\nby key? Use a dict.", UP)
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "My room is NOT\na hash map.", "Finding my socks\ntakes O(n).",
                  speech_punch="Finding my socks takes O of n.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()


class Thumbnail(ThumbnailMixin, HashMap):
    def design(self):
        """1 STEP: the hash machine sending a key straight into its bucket."""
        words = VGroup(headline_text("1 STEP.", 160, ACCENT), headline_text("Not a million.", 80, TEXT_LIGHT))
        if VERTICAL:  # Reels/Shorts cover: centered, clear of the cropped top and bottom
            words.arrange(DOWN, buff=0.15).move_to(UP * 4.5)
        else:
            words.arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(UL, buff=0.55)
        slots = VGroup(*[RoundedRectangle(width=0.95, height=0.7, corner_radius=0.1, fill_color="#232756", fill_opacity=1,
                                          stroke_color="#4A50A0", stroke_width=4) for _ in range(BUCKETS)])
        slots.arrange(RIGHT, buff=0.15).scale(pick(1, 0.82)).move_to(pick([-1.6, -2.7, 0], [0, 0.4, 0]))
        key = self.card("Bit", ACCENT).scale(1.5).move_to(pick([1.6, -0.6, 0], [0.9, 2.3, 0]))
        arrow = Arrow(key.get_bottom(), slots[4].get_top(), color=ACCENT, stroke_width=12, buff=0.1)
        slots[4].set_stroke(ACCENT, 6)
        bit = Bit().scale(1.5).move_to(pick([5.0, -1.2, 0], [0, -2.6, 0]))
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("raised"))
        bit.pose_arms(150, 150)
        self.add(slots, arrow, key, words, bit)
