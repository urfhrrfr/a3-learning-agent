"""
Mini intent classification evaluation.

This script uses only the Python standard library so it can run in a fresh
demo environment. It shows the full loop: samples, rule model, confusion
matrix, and error analysis.
"""

from collections import Counter, defaultdict


SAMPLES = [
    ("我想重置账号密码", "account"),
    ("登录以后一直提示验证码错误", "account"),
    ("这门课的发票在哪里下载", "billing"),
    ("我需要修改付款信息", "billing"),
    ("推荐一条机器学习学习路线", "learning"),
    ("怎么复习过拟合和泛化", "learning"),
]


KEYWORDS = {
    "account": ["密码", "登录", "验证码", "账号"],
    "billing": ["发票", "付款", "支付", "账单"],
    "learning": ["学习", "复习", "路线", "课程"],
}


def predict(text: str) -> str:
    scores = {
        label: sum(1 for keyword in keywords if keyword in text)
        for label, keywords in KEYWORDS.items()
    }
    return max(scores, key=scores.get)


def main() -> None:
    confusion = defaultdict(Counter)
    errors = []

    for text, expected in SAMPLES:
        actual = predict(text)
        confusion[expected][actual] += 1
        if actual != expected:
            errors.append((text, expected, actual))

    print("Confusion matrix")
    for expected, row in confusion.items():
        print(expected, dict(row))

    accuracy = sum(row[label] for label, row in confusion.items()) / len(SAMPLES)
    print(f"Accuracy: {accuracy:.2f}")
    print("Errors:", errors)


if __name__ == "__main__":
    main()
