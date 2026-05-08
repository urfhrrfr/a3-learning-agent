samples = [([0, 0], "基础"), ([1, 1], "基础"), ([5, 5], "提高"), ([6, 5], "提高")]
query = [2, 2]


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


nearest = min(samples, key=lambda item: distance(item[0], query))
print("预测层级:", nearest[1])
