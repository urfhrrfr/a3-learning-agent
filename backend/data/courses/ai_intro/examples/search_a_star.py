from heapq import heappop, heappush

graph = {
    "宿舍": {"图书馆": 4, "教学楼": 2},
    "教学楼": {"实验室": 5, "图书馆": 1},
    "图书馆": {"实验室": 2},
    "实验室": {},
}
heuristic = {"宿舍": 5, "教学楼": 3, "图书馆": 1, "实验室": 0}


def astar(start, goal):
    queue = [(heuristic[start], 0, start, [start])]
    visited = set()
    while queue:
        _, cost, node, path = heappop(queue)
        if node == goal:
            return path, cost
        if node in visited:
            continue
        visited.add(node)
        for nxt, step_cost in graph[node].items():
            heappush(queue, (cost + step_cost + heuristic[nxt], cost + step_cost, nxt, path + [nxt]))
    return [], float("inf")


print(astar("宿舍", "实验室"))
