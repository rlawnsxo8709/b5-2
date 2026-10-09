# 병합(merge) 후 `log` · `path` · `ancestors` 비교

아래 출력은 설명용 값이 아니라 **실제로 실행한 결과**다. 해시는 실행할 때마다 달라진다.

## 실행한 명령

```
init "Alice"
commit "root"
branch f
commit "m1"
switch f
commit "f1"
switch main
merge f
commit "c"
```

## 그래프

```
root(2b1feda) ─ m1(36b7993) ─┐
      └─ f1(f7be7fe) ────────┴─ M(c684a03) ─ c(29745b9)
```

- `main`에서 `merge f`를 하면 `f`의 이력이 `main`으로 합쳐지고, 부모가 둘(`m1`, `f1`)인 병합 커밋 `M`이 생긴다.
- 기존 커밋(`root`, `m1`, `f1`)은 그대로 남는다. 바뀌는 것은 `main` 브랜치 이름표가 `M`(이후 `c`)을 가리키는 것뿐이다.
- `f` 브랜치는 그대로 `f1`을 가리킨다.

## log

```
commit 2b1feda (Alice, 2026-10-09 21:16:07)
    root
commit 36b7993 (Alice, 2026-10-09 21:16:07)
    m1
commit f7be7fe (Alice, 2026-10-09 21:16:07) [f]
    f1
commit c684a03 (Alice, 2026-10-09 21:16:07) merge: 36b7993 f7be7fe
    Merge branch 'f' into main
commit 29745b9 (Alice, 2026-10-09 21:16:07) [HEAD -> main]
    c
```

모든 커밋이 한 번씩 나오고, 부모는 항상 자식보다 먼저 나온다. 병합 커밋 `M`은 두 부모(`m1`, `f1`) 뒤에 온다.

## path — 두 커밋 사이의 최단 경로 **하나**

```
path 2b1feda 29745b9        (root → c)
Path: 2b1feda -> 36b7993 -> c684a03 -> 29745b9
```

`m1` 경유와 `f1` 경유가 길이 3으로 같다. 경로의 두 번째 해시를 비교하면 `36b7993`이 `f7be7fe`보다 사전순으로 작아서(`3` < `f`) `m1` 쪽이 선택된다.

```
path 36b7993 f7be7fe        (m1 → f1)
Path: 36b7993 -> 2b1feda -> f7be7fe

path f7be7fe 36b7993        (f1 → m1)
Path: f7be7fe -> 2b1feda -> 36b7993
```

`m1`과 `f1`을 잇는 길은 `root` 경유와 `M` 경유가 길이 2로 같다. `root`(`2b1feda`)가 `M`(`c684a03`)보다 작아서 `root` 경유가 선택된다. 방향을 바꿔도 같은 길을 지난다.

## ancestors — 한 커밋의 조상 **전부**

```
ancestors 29745b9           (c의 조상)
Ancestors of 29745b9 (4):
- c684a03: Merge branch 'f' into main
- 36b7993: m1
- f7be7fe: f1
- 2b1feda: root
```

거리 1인 `M`이 먼저, 거리 2인 `m1`과 `f1`이 해시순으로 나오고, 거리 3인 `root`가 마지막이다. 병합의 **두 갈래가 모두** 나오고 `root`는 한 번만 나온다.

```
ancestors c684a03           (병합 커밋의 조상)
Ancestors of c684a03 (3):
- 36b7993: m1
- f7be7fe: f1
- 2b1feda: root

ancestors f7be7fe           (f1의 조상)
Ancestors of f7be7fe (1):
- 2b1feda: root
```

`f1`의 조상은 `root`뿐이다. 병합한 쪽(`main`)의 `m1`이나 자손 `M`은 나오지 않는다.

## 차이 요약

| | `log` | `path` | `ancestors` |
|---|---|---|---|
| 입력 | 없음 | 커밋 2개 | 커밋 1개 |
| 보는 방향 | 부모가 자식보다 먼저 | 부모·자식 모두 (무방향) | 부모 쪽만 |
| 결과 | 모든 커밋을 한 줄로 | 두 커밋을 잇는 최단 경로 **하나** | 그 커밋 위쪽의 조상 **전부** |
| 알고리즘 | 위상 정렬 (Kahn) | BFS (무방향) | BFS (부모 방향) |
| 병합이 있을 때 | 병합 커밋은 두 부모 뒤에 | 길이가 같은 길 중 해시가 작은 쪽 하나 | 두 갈래를 모두 따라가고 중복은 한 번만 |

- `path`는 형제 사이(`m1` ↔ `f1`)도 이을 수 있지만, `ancestors`는 형제를 보여 주지 않는다.
- 같은 거리에서의 선택 기준은 둘 다 **해시 문자열 사전순**이다. 16진수라서 `0`~`9`가 `a`~`f`보다 앞선다.
