"""Generate the original integer-grid Rowan sprite sheet; no image dependencies."""
from pathlib import Path

parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="192" height="24" viewBox="0 0 192 24" shape-rendering="crispEdges">']
for direction in range(4):
    for frame in range(3):
        parts.append(f'<g transform="translate({(direction * 3 + frame) * 16} 0)">')
        def rect(x, y, w, h, color):
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')
        rect(3, 21, 11, 2, '#27392c')
        rect(4, 18, 4, 4 if frame != 1 else 3, '#443e30')
        rect(9, 18, 4, 4 if frame != 2 else 3, '#443e30')
        rect(3, 12, 11, 7, '#8f5a3d')
        rect(4, 12, 9, 6, '#c18b51')
        rect(3, 17, 11, 2, '#5c4836')
        rect(8, 17, 2, 2, '#e5c37c')
        rect(2, 13 + (frame == 1), 2, 5, '#dfbb87')
        rect(13, 13 + (frame == 2), 2, 5, '#dfbb87')
        rect(5, 6, 8, 7, '#dfbb87')
        rect(4, 6, 3, 5, '#664b36')
        if direction != 3:
            if direction != 2: rect(7 if direction == 0 else 5, 9, 1, 2, '#2d3831')
            if direction != 1: rect(11 if direction == 0 else 12, 9, 1, 2, '#2d3831')
        else:
            rect(5, 7, 8, 5, '#664b36')
            rect(5, 13, 7, 6, '#586745')
            rect(6, 14, 5, 3, '#7e8a53')
        rect(4, 3, 10, 5, '#728052')
        rect(6, 1, 6, 3, '#8d9962')
        rect(2, 7, 13, 2, '#46533b')
        rect(4, 5, 10, 2, '#bca36b')
        rect(3, 1, 2, 5, '#ce9a58')
        parts.append('</g>')
parts.append('</svg>')
target = Path(__file__).resolve().parents[1] / 'frontend/public/art/rowan.svg'
target.write_text(''.join(parts), encoding='utf-8')
