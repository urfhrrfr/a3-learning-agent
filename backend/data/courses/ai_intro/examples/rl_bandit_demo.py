"""
Epsilon-greedy multi-armed bandit demo.

It is intentionally compact: students can change epsilon or reward means and
observe how exploration affects cumulative reward.
"""

import random


REWARD_MEANS = [0.2, 0.5, 0.8]


def pull(arm: int) -> float:
    return 1.0 if random.random() < REWARD_MEANS[arm] else 0.0


def choose_arm(values: list[float], epsilon: float) -> int:
    if random.random() < epsilon:
        return random.randrange(len(values))
    return max(range(len(values)), key=lambda index: values[index])


def run(steps: int = 100, epsilon: float = 0.1) -> None:
    counts = [0, 0, 0]
    values = [0.0, 0.0, 0.0]
    total_reward = 0.0

    for _ in range(steps):
        arm = choose_arm(values, epsilon)
        reward = pull(arm)
        counts[arm] += 1
        values[arm] += (reward - values[arm]) / counts[arm]
        total_reward += reward

    print("counts:", counts)
    print("estimated values:", [round(value, 2) for value in values])
    print("total reward:", total_reward)


if __name__ == "__main__":
    random.seed(7)
    run()
