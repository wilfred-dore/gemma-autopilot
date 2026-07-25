"""Manim Community scene: the math behind Gemma squared's optimization loop.

Pure Manim render (no browser capture) explaining the two objective search
under a hard latency constraint that the autopilot agent runs every time it
tunes the vLLM deployment.

Render:
    manim -pqh demo/manim/optimization_math.py OptimizationMath   # 1080p60
    manim -pqm demo/manim/optimization_math.py OptimizationMath   # fast draft
"""

from manim import (
    Axes,
    BLUE,
    Circle,
    DashedLine,
    Dot,
    DOWN,
    Create,
    Cross,
    FadeIn,
    FadeOut,
    GOLD,
    GREEN,
    GREY,
    LEFT,
    ORANGE,
    RED,
    Rectangle,
    RIGHT,
    Scene,
    Star,
    Text,
    UP,
    VGroup,
    Write,
    ManimColor,
)

INK = ManimColor("#e7e9ee")
BG = ManimColor("#0b0d12")
BROWN = ManimColor("#b98255")


class OptimizationMath(Scene):
    def construct(self):
        self.camera.background_color = BG

        # ---- 1. Title ------------------------------------------------
        title = Text("Gemma squared", font_size=56, color=INK, weight="BOLD")
        subtitle = Text(
            "The math behind an agent that tunes its own deployment",
            font_size=28,
            color=GREY,
        )
        subtitle.next_to(title, DOWN, buff=0.35)
        self.play(Write(title))
        self.play(FadeIn(subtitle, shift=UP * 0.2))
        self.wait(1.2)
        self.play(FadeOut(title), FadeOut(subtitle))

        # ---- 2. Define the two objectives ----------------------------
        header = Text("Two objectives, one hard constraint", font_size=38, color=INK)
        header.to_edge(UP)
        self.play(Write(header))

        obj1 = Text("T(c) = throughput, in tokens per second", font_size=30, color=INK)
        obj2 = Text("E(c) = 1 / (joules per token)", font_size=30, color=INK)
        constraint = Text("TTFT(c)  \u2264  500 ms", font_size=30, color=ORANGE)

        group = VGroup(obj1, obj2, constraint).arrange(DOWN, buff=0.6)
        group.next_to(header, DOWN, buff=0.8)

        self.play(Write(obj1))
        self.wait(0.4)
        self.play(Write(obj2))
        self.wait(0.4)
        self.play(Write(constraint))
        self.wait(1.5)

        goal = Text(
            "Goal: push T(c) and E(c) up together, while respecting the constraint",
            font_size=26,
            color=INK,
        )
        goal.next_to(group, DOWN, buff=0.9)
        self.play(FadeIn(goal, shift=UP * 0.2))
        self.wait(1.8)

        self.play(FadeOut(header), FadeOut(group), FadeOut(goal))

        # ---- 3. The search plane --------------------------------------
        axes = Axes(
            x_range=[0, 1600, 400],
            y_range=[0, 10, 2],
            x_length=9.5,
            y_length=5.2,
            axis_config={"color": GREY, "include_tip": True},
        )
        axes.to_edge(DOWN, buff=0.6)

        x_label = Text("throughput (tok/s)", font_size=24, color=GREY)
        x_label.next_to(axes.x_axis, RIGHT, buff=-1.0).shift(DOWN * 0.4)
        y_label = Text("efficiency", font_size=24, color=GREY)
        y_label.next_to(axes.y_axis, UP, buff=0.2)

        plane_title = Text("Every configuration is a point on this plane", font_size=32, color=INK)
        plane_title.to_edge(UP)

        self.play(Write(plane_title))
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label))
        self.wait(0.5)

        # Human baseline: conservative, low on both axes.
        p_baseline = axes.c2p(150, 2.2)
        dot_baseline = Dot(p_baseline, color=BROWN, radius=0.11)
        label_baseline = Text("human baseline", font_size=22, color=BROWN)
        label_baseline.next_to(dot_baseline, UP + LEFT * 0.3, buff=0.25)

        self.play(FadeIn(dot_baseline, scale=0.5), Write(label_baseline))
        self.wait(1.0)

        # Iteration 1: concurrency 8 -> 64, throughput jumps 406 -> 1377.
        p_iter1a = axes.c2p(406, 4.2)
        dot_iter1a = Dot(p_iter1a, color=BLUE, radius=0.1)
        arrow1a = DashedLine(p_baseline, p_iter1a, color=GREY)
        label_iter1a = Text("c = 8  →  406 tok/s", font_size=20, color=BLUE)
        label_iter1a.next_to(dot_iter1a, UP, buff=0.2)

        self.play(Create(arrow1a), FadeIn(dot_iter1a, scale=0.5), Write(label_iter1a))
        self.wait(0.8)

        p_iter1b = axes.c2p(1377, 6.0)
        dot_iter1b = Dot(p_iter1b, color=BLUE, radius=0.12)
        arrow1b = DashedLine(p_iter1a, p_iter1b, color=GREY)
        label_iter1b = Text("c = 64  →  1,377 tok/s", font_size=20, color=BLUE)
        label_iter1b.next_to(dot_iter1b, UP, buff=0.2)

        self.play(Create(arrow1b), FadeIn(dot_iter1b, scale=0.5), Write(label_iter1b))
        self.wait(1.2)

        # The guardrail: concurrency 128 pushes TTFT past 500ms -> rejected.
        guardrail_x = axes.c2p(1480, 0)[0]
        guardrail = DashedLine(
            [guardrail_x, axes.y_axis.get_start()[1], 0],
            [guardrail_x, axes.y_axis.get_end()[1], 0],
            color=RED,
        )
        guardrail_label = Text("TTFT > 500 ms  →  rejected", font_size=22, color=RED)
        guardrail_label.next_to(guardrail, UP, buff=0.15)

        p_rejected = axes.c2p(1520, 6.5)
        dot_rejected = Circle(radius=0.16, color=RED).move_to(p_rejected)
        cross1 = Cross(dot_rejected, stroke_color=RED, stroke_width=5, scale_factor=0.6)

        self.play(Create(guardrail), Write(guardrail_label))
        self.play(FadeIn(dot_rejected, scale=0.5), Write(cross1))
        self.wait(1.5)
        self.play(FadeOut(dot_rejected), FadeOut(cross1))

        # Pivot: cap GPU power instead -> efficiency recovers.
        p_iter3 = axes.c2p(1290, 8.0)
        dot_iter3 = Dot(p_iter3, color=GREEN, radius=0.11)
        arrow3 = DashedLine(p_iter1b, p_iter3, color=GREY)
        label_iter3 = Text("power cap  →  efficiency recovers", font_size=20, color=GREEN)
        label_iter3.next_to(dot_iter3, UP, buff=0.2)

        self.play(Create(arrow3), FadeIn(dot_iter3, scale=0.5), Write(label_iter3))
        self.wait(1.2)

        # Champion: best of both, constraint respected.
        p_champion = axes.c2p(1377, 8.6)
        star_champion = Star(color=GOLD, fill_opacity=1, outer_radius=0.22).move_to(p_champion)
        arrow4 = DashedLine(p_iter3, p_champion, color=GREY)
        label_champion = Text("champion: 1,377.5 tok/s, constraint respected", font_size=22, color=GOLD)
        label_champion.next_to(star_champion, UP, buff=0.25)

        self.play(Create(arrow4), FadeIn(star_champion, scale=0.5), Write(label_champion))
        self.wait(2.0)

        self.play(
            FadeOut(plane_title),
            FadeOut(axes),
            FadeOut(x_label),
            FadeOut(y_label),
            FadeOut(VGroup(dot_baseline, label_baseline)),
            FadeOut(VGroup(dot_iter1a, label_iter1a, arrow1a)),
            FadeOut(VGroup(dot_iter1b, label_iter1b, arrow1b)),
            FadeOut(VGroup(guardrail, guardrail_label)),
            FadeOut(VGroup(dot_iter3, label_iter3, arrow3)),
            FadeOut(VGroup(star_champion, label_champion, arrow4)),
        )

        # ---- 4. Results -------------------------------------------------
        result_title = Text("The result", font_size=40, color=INK)
        result_title.to_edge(UP)
        self.play(Write(result_title))

        bars_data = [
            ("defaults", 406, GREY),
            ("hand tuned expert", 1290, BROWN),
            ("Gemma squared", 1377.5, GOLD),
        ]
        max_val = 1500
        bar_group = VGroup()
        labels_group = VGroup()
        base_y = -2.2
        x_positions = [-3.5, 0, 3.5]
        for (name, value, color), x in zip(bars_data, x_positions):
            height = (value / max_val) * 4.0
            r = Rectangle(width=1.4, height=height, color=color, fill_color=color, fill_opacity=0.85)
            r.move_to([x, base_y + height / 2, 0])
            value_label = Text(f"{value:.0f} tok/s", font_size=22, color=INK)
            value_label.next_to(r, UP, buff=0.15)
            name_label = Text(name, font_size=22, color=color)
            name_label.next_to(r, DOWN, buff=0.2)
            bar_group.add(r)
            labels_group.add(value_label, name_label)

        self.play(*[FadeIn(r, shift=UP * 0.3) for r in bar_group])
        self.play(Write(labels_group))
        self.wait(1.5)

        delta1 = Text("+239% vs defaults", font_size=26, color=GOLD)
        delta2 = Text("+6.8% vs the hand tuned expert", font_size=26, color=GOLD)
        deltas = VGroup(delta1, delta2).arrange(DOWN, buff=0.3)
        deltas.next_to(bar_group, DOWN, buff=1.6)

        self.play(Write(deltas))
        self.wait(2.0)

        self.play(
            FadeOut(result_title),
            FadeOut(bar_group),
            FadeOut(labels_group),
            FadeOut(deltas),
        )

        # ---- 5. Closing ---------------------------------------------
        closing = Text("Every decision, explained.", font_size=44, color=INK, weight="BOLD")
        self.play(Write(closing))
        self.wait(2.0)
        self.play(FadeOut(closing))
