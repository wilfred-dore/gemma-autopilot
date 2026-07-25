from manim import *

BG = "#0b1020"
ACCENT = "#7dd3fc"
GOOD = "#4ade80"
WARM = "#fbbf24"


class GemmaLoop(Scene):
    def construct(self):
        self.camera.background_color = BG

        title = Text("Gemma²", font_size=64, color=ACCENT, weight=BOLD)
        sub = Text("Gemma 4 optimizes its own deployment", font_size=28, color=WHITE)
        sub.next_to(title, DOWN, buff=0.4)
        self.play(FadeIn(title), FadeIn(sub))
        self.wait(0.8)
        header = VGroup(title, sub)
        self.play(header.animate.scale(0.5).to_edge(UP, buff=0.3))

        labels = ["Profile", "Diagnose", "Act", "Re-benchmark"]
        positions = [LEFT * 4, UP * 1.6, RIGHT * 4, DOWN * 1.6]
        boxes = VGroup()
        for name, pos in zip(labels, positions):
            t = Text(name, font_size=26, color=WHITE)
            r = RoundedRectangle(corner_radius=0.15, width=t.width + 0.8,
                                 height=0.9, color=ACCENT, fill_color=BG,
                                 fill_opacity=1)
            g = VGroup(r, t).move_to(pos)
            boxes.add(g)

        arrows = VGroup()
        for i in range(4):
            a = CurvedArrow(boxes[i].get_center(),
                            boxes[(i + 1) % 4].get_center(),
                            angle=-0.9, color=WARM, tip_length=0.2)
            arrows.add(a)

        for i in range(4):
            self.play(FadeIn(boxes[i], scale=0.8), run_time=0.4)
            self.play(Create(arrows[i]), run_time=0.35)

        caption = Text("autonomous, guardrailed, explained", font_size=22,
                       color=WARM).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(caption))

        dot = Dot(color=GOOD, radius=0.09).move_to(boxes[0].get_center())
        self.add(dot)
        for _ in range(2):
            for i in range(4):
                self.play(MoveAlongPath(dot, arrows[i]), run_time=0.45)
        self.play(FadeOut(dot), FadeOut(caption))

        tps = ValueTracker(405.7)
        jpt = ValueTracker(0.768)
        tps_num = always_redraw(lambda: Text(
            f"{tps.get_value():,.1f}", font_size=48, color=GOOD,
            weight=BOLD).move_to(LEFT * 2.2 + UP * 0.3))
        jpt_num = always_redraw(lambda: Text(
            f"{jpt.get_value():.3f}", font_size=48, color=GOOD,
            weight=BOLD).move_to(RIGHT * 2.2 + UP * 0.3))
        tps_label = Text("tokens/s", font_size=24, color=WHITE).move_to(
            LEFT * 2.2 + DOWN * 0.5)
        jpt_label = Text("joules/token", font_size=24, color=WHITE).move_to(
            RIGHT * 2.2 + DOWN * 0.5)
        stats = VGroup(tps_label, jpt_label)

        self.play(FadeOut(boxes), FadeOut(arrows), FadeIn(stats))
        self.add(tps_num, jpt_num)
        self.play(tps.animate.set_value(1377.5), jpt.animate.set_value(0.353),
                  run_time=2.5, rate_func=rate_functions.ease_out_cubic)
        final_tps = Text("1,377.5", font_size=48, color=GOOD, weight=BOLD
                         ).move_to(LEFT * 2.2 + UP * 0.3)
        final_jpt = Text("0.353", font_size=48, color=GOOD, weight=BOLD
                         ).move_to(RIGHT * 2.2 + UP * 0.3)
        self.remove(tps_num, jpt_num)
        self.add(final_tps, final_jpt)
        stats = VGroup(tps_label, jpt_label, final_tps, final_jpt)
        delta = Text("+239% throughput   -54% energy   zero human intervention",
                     font_size=26, color=WARM).move_to(DOWN * 1.6)
        self.play(FadeIn(delta))
        self.wait(1.2)

        outro = Text("github.com/wilfred-dore/gemma-autopilot", font_size=30,
                     color=ACCENT)
        self.play(FadeOut(stats), FadeOut(delta), FadeOut(header),
                  FadeIn(outro))
        self.wait(1.5)
