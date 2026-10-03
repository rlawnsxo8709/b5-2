"""커밋 그래프 알고리즘. 저장소 상태를 모르는 순수 함수만 둔다.

그래프는 해시 문자열을 노드로 하고, 간선 조회는 호출자가 넘기는 함수
(parents_of, neighbors)로 받는다. 그래서 같은 함수를 LOG, PATH, ANCESTORS가 재사용한다.
"""

from collections import deque

from mini_git.sorting import merge_sort


def topo_order(nodes, parents_of):
    """Kahn 알고리즘으로 부모가 항상 자식보다 먼저 오는 순서를 만든다.

    nodes는 생성 순서(seq 오름차순)의 해시 리스트다. 지금 꺼낼 수 있는 노드(남은 부모가 0개)가
    여럿이면 nodes에서 앞선 노드를 먼저 꺼내므로 결과가 결정적이다. 사이클이 있으면 ValueError.

    시간복잡도: nodes가 생성 순서(부모가 항상 앞)이면 가장 앞에 남은 노드가 늘 꺼낼 수 있는 상태라
    탐색 포인터가 되돌아가지 않아 O(V + E)다. 임의 순서의 nodes에서는 최악 O(V^2)까지 늘어날 수 있다.
    """
    position = {h: i for i, h in enumerate(nodes)}
    waiting = [0] * len(nodes)  # 아직 출력되지 않은 부모의 수
    children = {h: [] for h in nodes}
    for h in nodes:
        for p in parents_of(h):
            waiting[position[h]] += 1
            children[p].append(h)

    ready = [count == 0 for count in waiting]
    order = []
    lo = 0  # 이 위치 앞에는 꺼낼 수 있는 노드가 없다
    while True:
        while lo < len(nodes) and not ready[lo]:
            lo += 1
        if lo == len(nodes):
            break
        h = nodes[lo]
        ready[lo] = False
        lo += 1
        order.append(h)
        for child in children[h]:
            idx = position[child]
            waiting[idx] -= 1
            if waiting[idx] == 0:
                ready[idx] = True
                if idx < lo:
                    lo = idx
    if len(order) != len(nodes):
        raise ValueError("cycle detected in commit graph")
    return order


def shortest_path(start, goal, neighbors):
    """무방향 그래프에서 간선 수가 최소인 경로를 돌려준다. 동률이면 `h1->h2->...` 사전순 최소. 없으면 None.

    1. goal에서 BFS를 돌려 모든 노드까지의 거리 dist를 구한다.
    2. start에서 출발해 dist가 1씩 줄어드는 이웃 중 해시가 가장 작은 노드를 고른다.

    모든 해시의 길이가 같으므로 경로 문자열의 사전순 비교는 처음으로 달라지는 노드의 해시 비교와 같다.
    그래서 각 단계에서 가장 작은 해시를 고르는 탐욕 선택이 문자열 전체의 사전순 최소를 보장한다.
    (이 증명은 해시 길이가 고정이라는 전제 위에 있다. Repository가 7자리로 고정한다.)
    """
    if start == goal:
        return [start]
    dist = {goal: 0}
    queue = deque([goal])
    while queue:
        cur = queue.popleft()
        for nxt in neighbors(cur):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)
    if start not in dist:
        return None

    path = [start]
    cur = start
    while cur != goal:
        closer = [n for n in neighbors(cur) if dist.get(n) == dist[cur] - 1]
        cur = min(closer)
        path.append(cur)
    return path


def ancestors(start, parents_of):
    """start에서 부모 방향으로 도달 가능한 모든 조상을 BFS 순서로 돌려준다(start 제외).

    가까운 조상부터 나오고, 같은 거리에서는 해시 오름차순이다. 방문 집합으로 합류 지점의
    조상이 중복 출력되지 않게 한다. 시간복잡도 O(V + E) (같은 거리 안의 정렬 비용 제외).
    """
    visited = {start}
    result = []
    frontier = [start]
    while frontier:
        found = []
        for h in frontier:
            for p in parents_of(h):
                if p not in visited:
                    visited.add(p)
                    found.append(p)
        frontier = merge_sort(found)
        result.extend(frontier)
    return result
