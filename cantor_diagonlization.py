from manim import *


#manim -pqh cantor_diagonalization.py CantorDiagonalization --to run at high quality

class CantorDiagonalization(Scene):
    """
    Visual explanation of Cantor's diagonalization proof.

    The proof is shown using decimal expansions whose digits are only
    1 and 2. This avoids the usual ambiguity caused by decimals such
    as 0.4999... = 0.5000...
    """

    def construct(self):
        self.camera.background_color = "#0B1020"

        # ------------------------------------------------------------------
        # Palette
        # ------------------------------------------------------------------
        white = "#F4F7FB"
        muted = "#AAB6CC"
        blue = "#58A6FF"
        cyan = "#55D6BE"
        yellow = "#FFD166"
        green = "#63E6BE"
        red = "#FF6B6B"
        panel_color = "#121B32"
        cell_color = "#172440"

        # ------------------------------------------------------------------
        # Title
        # ------------------------------------------------------------------
        title = Text(
            "Cantor’s Diagonalization",
            font_size=42,
            weight=BOLD,
            color=white,
        ).to_edge(UP, buff=0.28)

        subtitle = Text(
            "Why the real numbers cannot be listed like the natural numbers",
            font_size=20,
            color=muted,
        ).next_to(title, DOWN, buff=0.12)

        self.play(FadeIn(title, shift=DOWN * 0.2))
        self.play(FadeIn(subtitle, shift=DOWN * 0.15))
        self.wait(0.8)

        # ------------------------------------------------------------------
        # Introductory statement
        # ------------------------------------------------------------------
        intro = VGroup(
            Text(
                "Suppose, for contradiction, that every real number in [0, 1]",
                font_size=22,
                color=white,
            ),
            Text(
                "could be placed into one infinite list.",
                font_size=22,
                color=white,
            ),
        ).arrange(DOWN, buff=0.08)

        intro_box = SurroundingRectangle(
            intro,
            color=blue,
            corner_radius=0.12,
            buff=0.22,
        )
        intro_box.set_fill(panel_color, opacity=0.85)

        intro_group = VGroup(intro_box, intro).shift(DOWN * 0.25)

        self.play(FadeIn(intro_group, shift=DOWN * 0.2))
        self.wait(1.2)
        self.play(FadeOut(intro_group))
        self.wait(0.4)

        # ------------------------------------------------------------------
        # Create a hypothetical list of real numbers
        # ------------------------------------------------------------------
        rows = 7
        cols = 9

        # Digits use only 1 and 2, avoiding decimal representation ambiguity.
        digit_rows = [
            "121221212",
            "212112221",
            "221211122",
            "112212112",
            "122121221",
            "211222111",
            "212121212",
        ]

        table_group = VGroup()
        cells = []

        table_y = 1.18
        start_x = -2.75
        dx = 0.55
        dy = 0.49

        # Table heading
        list_heading = Text(
            "A hypothetical complete list",
            font_size=23,
            color=white,
            weight=BOLD,
        ).move_to((-0.9, 2.58, 0))

        list_subheading = Text(
            "Each row is a real number in [0, 1]",
            font_size=16,
            color=muted,
        ).next_to(list_heading, DOWN, buff=0.07)

        table_group.add(list_heading, list_subheading)

        # Column guide
        decimal_marker = Text(
            "0.",
            font_size=22,
            color=muted,
        ).move_to((start_x - 0.63, table_y + 0.22, 0))
        table_group.add(decimal_marker)

        for r in range(rows):
            row_cells = []

            row_number = Text(
                f"{r + 1}",
                font_size=19,
                color=muted,
            ).move_to((start_x - 1.0, table_y - r * dy, 0))

            table_group.add(row_number)

            for c in range(cols):
                cell = RoundedRectangle(
                    width=0.46,
                    height=0.39,
                    corner_radius=0.06,
                    stroke_width=1.2,
                    stroke_color="#31466E",
                    fill_color=cell_color,
                    fill_opacity=1,
                ).move_to((start_x + c * dx, table_y - r * dy, 0))

                digit = Text(
                    digit_rows[r][c],
                    font_size=21,
                    color=white,
                    weight=BOLD,
                ).move_to(cell.get_center())

                cell_group = VGroup(cell, digit)
                table_group.add(cell_group)
                row_cells.append(cell_group)

            cells.append(row_cells)

        # Right-hand explanation panel
        panel = RoundedRectangle(
            width=3.05,
            height=2.35,
            corner_radius=0.16,
            stroke_color=blue,
            stroke_width=1.5,
            fill_color=panel_color,
            fill_opacity=0.95,
        ).move_to((4.35, 0.55, 0))

        panel_title = Text(
            "The key assumption",
            font_size=20,
            color=yellow,
            weight=BOLD,
        ).move_to((4.35, 1.35, 0))

        panel_text = VGroup(
            Text("The list claims to contain", font_size=17, color=white),
            Text("every real number in [0, 1].", font_size=17, color=white),
            Text("We will construct one", font_size=17, color=white),
            Text("that cannot appear in it.", font_size=17, color=green),
        ).arrange(DOWN, buff=0.1).move_to((4.35, 0.53, 0))

        panel_group = VGroup(panel, panel_title, panel_text)

        self.play(
            LaggedStart(
                FadeIn(table_group, shift=UP * 0.2),
                FadeIn(panel_group, shift=LEFT * 0.2),
                lag_ratio=0.15,
            ),
            run_time=1.8,
        )
        self.wait(1)

        # ------------------------------------------------------------------
        # Highlight the diagonal
        # ------------------------------------------------------------------
        diagonal_boxes = VGroup()

        diagonal_label = Text(
            "Read the diagonal digits",
            font_size=20,
            color=yellow,
            weight=BOLD,
        ).to_edge(LEFT, buff=0.55).shift(DOWN * 2.55)

        self.play(FadeIn(diagonal_label, shift=RIGHT * 0.15))

        for i in range(min(rows, cols)):
            box = SurroundingRectangle(
                cells[i][i],
                color=yellow,
                stroke_width=3,
                buff=0.035,
            )
            diagonal_boxes.add(box)
            self.play(Create(box), run_time=0.28)

        self.wait(0.8)

        # ------------------------------------------------------------------
        # Construct the diagonal number by flipping every diagonal digit
        # ------------------------------------------------------------------
        construction_text = Text(
            "Flip each diagonal digit: 1 ↔ 2",
            font_size=20,
            color=cyan,
            weight=BOLD,
        ).to_edge(LEFT, buff=0.55).shift(DOWN * 2.55)

        self.play(
            ReplacementTransform(diagonal_label, construction_text),
            run_time=0.5,
        )

        output_y = -2.35
        output_x = start_x

        output_label = Text(
            "new number  x = 0.",
            font_size=22,
            color=green,
            weight=BOLD,
        ).move_to((-4.03, output_y, 0))

        self.play(FadeIn(output_label, shift=RIGHT * 0.15))

        output_digits = VGroup()

        for i in range(min(rows, cols)):
            original_digit = digit_rows[i][i]
            flipped_digit = "2" if original_digit == "1" else "1"

            new_digit = Text(
                flipped_digit,
                font_size=23,
                color=green,
                weight=BOLD,
            ).move_to((output_x + i * dx, output_y, 0))

            output_digits.add(new_digit)

            self.play(
                FadeIn(new_digit, shift=UP * 0.12),
                Indicate(cells[i][i], color=yellow, scale_factor=1.08),
                run_time=0.38,
            )

        ellipsis = Text(
            "…",
            font_size=25,
            color=green,
        ).move_to((output_x + cols * dx, output_y, 0))

        self.play(FadeIn(ellipsis))
        self.wait(1)

        # ------------------------------------------------------------------
        # Explain why the new number is not on the list
        # ------------------------------------------------------------------
        contradiction = VGroup(
            Text(
                "x differs from row 1 in digit 1,",
                font_size=18,
                color=white,
            ),
            Text(
                "from row 2 in digit 2,",
                font_size=18,
                color=white,
            ),
            Text(
                "from row 3 in digit 3, and so on.",
                font_size=18,
                color=white,
            ),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.06)

        contradiction_box = SurroundingRectangle(
            contradiction,
            color=green,
            corner_radius=0.12,
            buff=0.18,
        )
        contradiction_box.set_fill(panel_color, opacity=0.9)

        contradiction_group = VGroup(
            contradiction_box,
            contradiction,
        ).move_to((3.9, -1.75, 0))

        self.play(FadeIn(contradiction_group, shift=LEFT * 0.2))
        self.wait(1.5)

        # ------------------------------------------------------------------
        # Final conclusion
        # ------------------------------------------------------------------
        everything_except_title = VGroup(
            table_group,
            panel_group,
            diagonal_boxes,
            construction_text,
            output_label,
            output_digits,
            ellipsis,
            contradiction_group,
        )

        self.play(
            everything_except_title.animate.scale(0.82).shift(UP * 0.35),
            run_time=0.8,
        )

        conclusion_box = RoundedRectangle(
            width=10.8,
            height=1.35,
            corner_radius=0.18,
            stroke_color=cyan,
            stroke_width=2,
            fill_color="#10283A",
            fill_opacity=0.96,
        ).move_to((0, -2.55, 0))

        conclusion = VGroup(
            Text(
                "No proposed list can contain every real number.",
                font_size=25,
                color=white,
                weight=BOLD,
            ),
            Text(
                "Therefore, the real numbers are uncountable.",
                font_size=25,
                color=green,
                weight=BOLD,
            ),
        ).arrange(DOWN, buff=0.12).move_to(conclusion_box.get_center())

        self.play(
            FadeIn(conclusion_box, shift=UP * 0.2),
            FadeIn(conclusion, shift=UP * 0.2),
            run_time=1,
        )
        self.wait(2)

        # Final comparison with the natural numbers
        comparison = VGroup(
            Text("Natural numbers:", font_size=20, color=muted),
            MathTex(r"\mathbb{N} = \{1,2,3,\ldots\}", color=white),
            Text("Real numbers:", font_size=20, color=muted),
            MathTex(r"\mathbb{R} \text{ contains more elements than } \mathbb{N}", color=green),
        ).arrange(DOWN, buff=0.1)

        comparison.to_edge(DOWN, buff=0.18)

        self.play(FadeIn(comparison, shift=UP * 0.15))
        self.wait(3)