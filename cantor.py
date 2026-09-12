import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle


# ----------------------------
# Configuration
# ----------------------------

N = 16                  # Number of rows and columns to display
RANDOM_SEED = 7         # Change this to generate a different example


# ----------------------------
# Generate a finite list of
# binary sequences
# ----------------------------

rng = np.random.default_rng(RANDOM_SEED)

# Each row is one binary sequence
sequences = rng.integers(0, 2, size=(N, N))

# Cantor's diagonal sequence:
# Flip the nth bit of the nth sequence
diagonal_sequence = 1 - np.diag(sequences)


# ----------------------------
# Create the visualization
# ----------------------------

fig = plt.figure(figsize=(13, 9))
grid = fig.add_gridspec(
    nrows=3,
    ncols=1,
    height_ratios=[8, 1.8, 1.2],
    hspace=0.45
)

# Use white for 0 and dark purple for 1
colors = ["white", "#542788"]
cmap = ListedColormap(colors)


# ----------------------------
# Main binary table
# ----------------------------

ax = fig.add_subplot(grid[0])

ax.imshow(
    sequences,
    cmap=cmap,
    vmin=0,
    vmax=1,
    aspect="auto",
    interpolation="none"
)

# Write each bit inside its cell
for row in range(N):
    for col in range(N):
        bit = sequences[row, col]

        ax.text(
            col,
            row,
            str(bit),
            ha="center",
            va="center",
            fontsize=11,
            color="black" if bit == 0 else "white",
            fontweight="bold"
        )

# Highlight the diagonal cells
for i in range(N):
    ax.add_patch(
        Rectangle(
            (i - 0.48, i - 0.48),
            0.96,
            0.96,
            fill=False,
            edgecolor="red",
            linewidth=2.5
        )
    )

# Axis labels and ticks
ax.set_xticks(range(N))
ax.set_xticklabels([f"{i + 1}" for i in range(N)])
ax.set_yticks(range(N))
ax.set_yticklabels([f"Sequence {i + 1}" for i in range(N)])

ax.set_xlabel("Bit position")
ax.set_ylabel("Listed sequence")

ax.set_title(
    "Cantor's Diagonalization Argument",
    fontsize=17,
    fontweight="bold",
    pad=15
)

# Grid lines
ax.set_xticks(np.arange(-0.5, N, 1), minor=True)
ax.set_yticks(np.arange(-0.5, N, 1), minor=True)
ax.grid(which="minor", color="gray", linewidth=0.7)
ax.tick_params(which="minor", bottom=False, left=False)

# Explanation of the red diagonal
ax.text(
    N + 0.25,
    N * 0.35,
    "Red cells:\n"
    "diagonal bits\n"
    r"$x^{(n)}_n$",
    color="red",
    fontsize=12,
    va="center",
    bbox=dict(
        boxstyle="round,pad=0.5",
        facecolor="#fff5f5",
        edgecolor="red"
    )
)


# ----------------------------
# Constructed sequence
# ----------------------------

ax2 = fig.add_subplot(grid[1])

ax2.imshow(
    diagonal_sequence.reshape(1, -1),
    cmap=cmap,
    vmin=0,
    vmax=1,
    aspect="auto",
    interpolation="none"
)

for col, bit in enumerate(diagonal_sequence):
    ax2.text(
        col,
        0,
        str(bit),
        ha="center",
        va="center",
        fontsize=12,
        color="black" if bit == 0 else "white",
        fontweight="bold"
    )

    # Highlight the newly constructed sequence
    ax2.add_patch(
        Rectangle(
            (col - 0.48, -0.48),
            0.96,
            0.96,
            fill=False,
            edgecolor="#2166ac",
            linewidth=2.5
        )
    )

ax2.set_xticks(range(N))
ax2.set_xticklabels([f"{i + 1}" for i in range(N)])
ax2.set_yticks([0])
ax2.set_yticklabels(["New sequence"])

ax2.set_xlabel("Bit position")
ax2.set_title(
    "Constructed sequence: flip every diagonal bit",
    color="#2166ac",
    fontweight="bold"
)

ax2.set_xticks(np.arange(-0.5, N, 1), minor=True)
ax2.grid(which="minor", color="gray", linewidth=0.7)
ax2.tick_params(which="minor", bottom=False, left=False)


# ----------------------------
# Explanation panel
# ----------------------------

ax3 = fig.add_subplot(grid[2])
ax3.axis("off")

explanation = (
    "For every row n, the constructed sequence differs at position n. "
    "Therefore it differs from row 1 at position 1, row 2 at position 2, "
    "row 3 at position 3, and so on. It cannot be anywhere in the list."
)

ax3.text(
    0.5,
    0.5,
    explanation,
    ha="center",
    va="center",
    fontsize=12,
    bbox=dict(
        boxstyle="round,pad=0.7",
        facecolor="#eef5ff",
        edgecolor="#2166ac"
    )
)

fig.text(
    0.5,
    0.01,
    "This finite display illustrates the pattern of the infinite proof.",
    ha="center",
    fontsize=10,
    style="italic"
)

plt.show()
