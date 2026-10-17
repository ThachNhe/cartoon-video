"""Binary search: find a number in a sorted list by always checking the middle.

Bit first scans a list one tile at a time, then halves it: four guesses instead of eleven,
and twenty guesses for a million items. The catch: the list must be sorted.

Render:  .venv/bin/manim -qh --fps 30 binary_search.py BinarySearch
Vertical 9:16 (Shorts/Reels):
    BIT_FORMAT=vertical .venv/bin/manim -qh --fps 30 binary_search.py BinarySearch
Thumbnail: .venv/bin/manim -s -r 1280,720 binary_search.py Thumbnail
"""

from bitbybit import *

NUMBERS = [3, 8, 12, 17, 23, 31, 38, 42, 50, 56, 61, 69, 77, 84, 95]
TARGET = 61
TARGET_INDEX = NUMBERS.index(TARGET)
SHUFFLED = [77, 12, 95, 3, 50, 31, 84, 69, 8, 61, 23, 42, 17, 56, 38]

# 16:9 lays the tiles out in a row, 9:16 in a column: halving always uses the long side.
TILE = pick((0.74, 0.74), (1.3, 0.56))  # width, height
TILES_AT = pick([0, 0.9, 0], [-2.0, 1.15, 0])
BIT_AT = pick([0, -2.7, 0], [1.9, -1.4, 0])
SIDE_AT = pick([4.6, 2.6, 0], [1.9, 3.6, 0])  # guess counter and comparisons


def binary_steps(values, target):
    """(lo, mid, hi) for every guess, as the textbook loop makes them."""
    lo, hi, steps = 0, len(values) - 1, []
    while lo <= hi:
        mid = (lo + hi) // 2
        steps.append((lo, mid, hi))
        if values[mid] == target:
            break
        lo, hi = (mid + 1, hi) if values[mid] < target else (lo, mid - 1)
    return steps


class BinarySearch(BitScene):
    # ---------------------------------------------------------------- pieces
    def tiles(self, values):
        w, h = TILE
        row = VGroup()
        for v in values:
            box = RoundedRectangle(width=w, height=h, corner_radius=0.1, fill_color="#2C3166", fill_opacity=1,
                                   stroke_color="#4A50A0", stroke_width=3)
            row.add(VGroup(box, Text(str(v), font=MONO, weight=BOLD, font_size=28, color=TEXT_LIGHT).move_to(box)))
        return row.arrange(pick(RIGHT, DOWN), buff=0.07).move_to(TILES_AT)

    def pointer(self, tile, color=ACCENT):
        """Arrow at a tile: from below in a row, from the right in a column."""
        side = pick(DOWN, RIGHT)
        return Arrow(tile.get_edge_center(side) + side * 0.75, tile.get_edge_center(side), color=color, buff=0.05,
                     stroke_width=8, max_tip_length_to_length_ratio=0.45)

    def counter(self, label, value=0):
        text = Text(f"{label}: {value}", font=MONO, weight=BOLD, font_size=34, color=TEXT_LIGHT)
        return text.move_to(SIDE_AT)

    def line(self, bit, text, **kwargs):
        return self.say(bit, text, UP, shift=RIGHT * 0.2, font_size=pick(34, 30), **kwargs)

    def hook_visual(self):
        """A million tiles and a worried Bit."""
        dots = VGroup(*[
            Square(0.16, stroke_width=0, fill_color="#4A50A0", fill_opacity=0.25 + 0.5 * ((r * 7 + c * 3) % 5) / 5)
            for r in range(36) for c in range(22)
        ]).arrange_in_grid(36, 22, buff=0.06).move_to(DOWN * 1.2)
        big = headline_text("1,000,000", 120, ACCENT).move_to(UP * 0.6)
        big.scale_to_fit_width(min(big.width, config.frame_width - 0.8))
        bit = self.shocked_bit(1.0).move_to(DOWN * 3.6)
        return Group(dots, big, bit)

    # -------------------------------------------------------------- timeline
    def construct(self):
        self.camera.background_color = BG
        self.stage()
        if SHORT:
            self.chapter("cold_open", "A million items, 20 guesses?")
            self.hook_open(("Find 1 number in a MILLION", "in just 20 guesses?"),
                           "Find one number in a million, in just twenty guesses?", sound="boing", shake=False)
        self.chapter("intro", "Intro")
        bit, title = self.title_intro("BINARY SEARCH", "Binary search.")
        self.chapter("meet", "Searching one by one")
        bit, tiles = self.one_by_one(bit, title)
        self.chapter("halves", "Check the middle, throw away half")
        self.halves(bit, tiles)
        self.chapter("million", "A million items in 20 guesses")
        self.million(bit)
        if not SHORT:  # the short cut keeps the lesson in its headline: "Sorted list?"
            self.chapter("catch", "The catch: it must be sorted")
            self.catch(bit)
        else:
            self.sfx("whoosh")
            self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
            self.stage()
        self.chapter("joke", "The binary search joke")
        self.punchline()
        self.chapter("outro", "Recap")
        self.ending(pick(["Sorted list? Search in halves."], ["Sorted list?", "Search in halves."]),
                    "Halve the search time.\nDouble the subscribers!",
                    loop_line="So... how many guesses\nfor a MILLION?", loop_finale=self.hook_look)

    def one_by_one(self, bit, title):
        if not SHORT:
            self.say(bit, "Hi! I'm Bit.", UR, gesture=bit.wave())
            self.moment("promise")
            self.say(bit, "Today: find anything in a\nMILLION items, in 20 steps.", UR, gesture=bit.point(0, 165))
        tiles = self.tiles(NUMBERS)
        self.sfx("whoosh")
        self.play(FadeOut(title, shift=UP * 0.8), bit.arms_rest(run_time=0.3), run_time=0.35)
        self.play(bit.animate.scale(0.7).move_to(BIT_AT), run_time=0.4)
        self.sfx("pop")
        self.play(LaggedStart(*[FadeIn(t, shift=pick(UP, LEFT) * 0.3) for t in tiles], lag_ratio=0.08), run_time=0.8)
        self.line(bit, "A sorted list.\nWhere is 61?",
                 speech="A sorted list. Where is sixty-one?")

        # The slow way: check every tile from the start.
        checks = self.counter("checks")
        self.play(FadeIn(checks), bit.look(pick(UP, LEFT)), run_time=0.2)
        arrow = self.pointer(tiles[0])
        self.play(GrowArrow(arrow), run_time=0.2)
        for i in range(NUMBERS.index(TARGET) + 1):
            self.sfx("blip", gain=-6)
            new = self.counter("checks", i + 1)
            self.play(arrow.animate.become(self.pointer(tiles[i])), checks.animate.become(new), run_time=0.16)
        self.sfx("ding")
        self.play(tiles[TARGET_INDEX][0].animate.set_fill(CONSOLE_GREEN, 0.6), run_time=0.2)
        self.moment("gag")
        self.line(bit, "11 checks. Fine for 15 items...\nnot for a million.", speech="Eleven checks. Fine for fifteen items... not for a million.")
        self.play(FadeOut(arrow), FadeOut(checks), tiles[TARGET_INDEX][0].animate.set_fill("#2C3166", 1), run_time=0.3)
        return bit, tiles

    def halves(self, bit, tiles):
        self.line(bit, "Smarter: look at the MIDDLE.\nThen throw away half.", gesture=bit.point(pick(1, 0), pick(80, 120)),
                 speech="Smarter: look at the middle. Then throw away half.")
        self.play(bit.arms_rest(run_time=0.2), run_time=0.2)
        guesses = self.counter("guesses")
        self.play(FadeIn(guesses), run_time=0.2)
        arrow = None
        for n, (lo, mid, hi) in enumerate(binary_steps(NUMBERS, TARGET)):
            tile, value = tiles[mid], NUMBERS[mid]
            new_arrow = self.pointer(tile)
            self.sfx("pop")
            self.play(arrow.animate.become(new_arrow) if arrow else GrowArrow(new_arrow),
                      guesses.animate.become(self.counter("guesses", n + 1)),
                      tile[0].animate.set_stroke(ACCENT, 6), run_time=0.3)
            arrow = arrow or new_arrow
            if value == TARGET:
                break
            sign = "<" if value < TARGET else ">"
            note = Text(f"{value} {sign} 61", font=MONO, weight=BOLD, font_size=36, color=ACCENT)
            note.next_to(guesses, DOWN, buff=0.3)
            gone = [tiles[i] for i in (range(lo, mid + 1) if value < TARGET else range(mid, hi + 1))]
            self.play(FadeIn(note, scale=1.2), run_time=0.25)
            self.sfx("whoosh", gain=-6)
            self.play(*[t.animate.set_opacity(0.18) for t in gone], FadeOut(note), run_time=0.45)
        self.moment("reveal")
        self.sfx("ding")
        self.play(tiles[TARGET_INDEX][0].animate.set_fill(CONSOLE_GREEN, 0.7), Flash(tiles[TARGET_INDEX], color=ACCENT),
                  bit.express("grin", "raised"), bit.arms_up(run_time=0.3), run_time=0.4)
        self.line(bit, "Found it in 4 guesses,\nnot 11!",
                 speech="Found it in four guesses, not eleven!")
        self.sfx("whoosh")
        self.play(FadeOut(tiles), FadeOut(arrow), FadeOut(guesses), bit.arms_rest(run_time=0.3),
                  bit.express("smile", "neutral"), run_time=0.4)

    def million(self, bit):
        size = 1_000_000
        number = headline_text(f"{size:,}", 110, ACCENT).move_to(pick(UP * 1.6, UP * 3.4))
        caption = Text("items left", font=FONT, font_size=34, color=TEXT_MUTED).next_to(number, DOWN, buff=0.25)
        guesses = self.counter("guesses").next_to(caption, DOWN, buff=0.5)
        self.play(FadeIn(number, scale=0.8), FadeIn(caption), FadeIn(guesses), run_time=0.4)
        self.line(bit, "Now a MILLION items.\nEvery guess cuts it in half.",
                 speech="Now a million items. Every guess cuts it in half.")
        for n in range(1, 21):
            size = max(1, size // 2)
            self.sfx("blip" if n < 20 else "ding", gain=-4)
            self.play(number.animate.become(headline_text(f"{size:,}", 110, ACCENT).move_to(number)),
                      guesses.animate.become(self.counter("guesses", n).move_to(guesses)), run_time=0.13)
        self.moment("payoff")
        self.play(Flash(number, color=ACCENT, flash_radius=1.6), bit.express("grin", "raised"),
                  bit.arms_up(run_time=0.3), run_time=0.5)
        self.line(bit, "20 guesses. One by one,\nit could take a MILLION!", speech="Twenty guesses. One by one, it could take a million!")
        self.sfx("whoosh")
        self.play(FadeOut(number), FadeOut(caption), FadeOut(guesses), bit.arms_rest(run_time=0.3),
                  bit.express("smile", "neutral"), run_time=0.4)

    def catch(self, bit):
        tiles = self.tiles(SHUFFLED)
        self.moment("twist")
        self.sfx("whoosh")
        self.play(LaggedStart(*[FadeIn(t, shift=pick(UP, LEFT) * 0.3) for t in tiles], lag_ratio=0.05), run_time=0.6)
        self.line(bit, "But what if the list\nis NOT sorted?")
        mid = len(SHUFFLED) // 2
        arrow = self.pointer(tiles[mid])
        self.sfx("pop")
        self.play(GrowArrow(arrow), tiles[mid][0].animate.set_stroke(ACCENT, 6), run_time=0.3)
        # 69 > 61, so binary search throws away the right half... where 61 actually is.
        self.play(*[tiles[i].animate.set_opacity(0.18) for i in range(mid, len(SHUFFLED))], run_time=0.4)
        self.sfx("oops")
        self.play(Indicate(tiles[SHUFFLED.index(TARGET)], color=RED, scale_factor=1.3), bit.express("open", "worried"),
                  run_time=0.6)
        self.line(bit, "69 > 61, so it tossed the half\nwith 61 in it. Not found!", speech="Sixty-nine is bigger, so it tossed the half with sixty-one in it. Not found!")
        self.line(bit, "Binary search only works\non a SORTED list.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.5)
        self.stage()

    def punchline(self):
        bit = Bit().move_to(pick([-4.2, -0.8, 0], [-1.6, -1.6, 0]))
        self.play(FadeIn(bit, shift=RIGHT * 2), run_time=0.4)
        self.joke(bit, "I used binary search\nto find my keys.", "Step one:\nsort the whole house.")
        self.sfx("whoosh")
        self.play(*[FadeOut(m) for m in self.top_level()[1:]], run_time=0.4)
        self.stage()



class Thumbnail(ThumbnailMixin, BinarySearch):
    def design(self):
        """1,000,000 → 20: a halving staircase of tiles and an amazed Bit."""
        steps = VGroup()
        width = 6.4
        for k in range(6):
            bar = RoundedRectangle(width=width, height=0.42, corner_radius=0.1, stroke_width=0,
                                   fill_color=ACCENT if k == 5 else "#4A50A0", fill_opacity=1)
            steps.add(bar)
            width /= 2
        steps.arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([-3.0, -1.9, 0])
        words = VGroup(headline_text("1,000,000", 130, ACCENT), headline_text("in 20 GUESSES", 96, TEXT_LIGHT))
        words.arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(UL, buff=0.55)
        bit = Bit().scale(1.7).move_to([4.2, -1.0, 0])
        bit.mouth.become(bit.make_mouth("grin"))
        bit.brows.become(bit.make_brows("raised"))
        bit.pose_arms(150, 150)
        self.add(steps, words, bit)
