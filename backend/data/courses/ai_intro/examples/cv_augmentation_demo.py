"""
Tiny image augmentation demo without external libraries.

Pixels are represented as nested lists. The goal is to observe how horizontal
flip and brightness changes alter simple features while keeping the class idea.
"""


IMAGE = [
    [0, 0, 1, 1],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 0],
]


def flip_horizontal(image: list[list[int]]) -> list[list[int]]:
    return [list(reversed(row)) for row in image]


def brighten(image: list[list[int]], amount: int = 1) -> list[list[int]]:
    return [[min(pixel + amount, 2) for pixel in row] for row in image]


def feature_summary(image: list[list[int]]) -> dict[str, int]:
    left_half = sum(sum(row[:2]) for row in image)
    right_half = sum(sum(row[2:]) for row in image)
    total = left_half + right_half
    return {"left": left_half, "right": right_half, "total": total}


def show(name: str, image: list[list[int]]) -> None:
    print(name, feature_summary(image))
    for row in image:
        print(" ".join(str(pixel) for pixel in row))
    print()


if __name__ == "__main__":
    show("original", IMAGE)
    show("flipped", flip_horizontal(IMAGE))
    show("brightened", brighten(IMAGE))
