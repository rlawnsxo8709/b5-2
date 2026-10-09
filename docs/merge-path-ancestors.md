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

---

# 동률일 때 무엇을 보는가: 해시 vs 만든 순서

세 명령 모두 "순서가 자유로운 커밋이 여럿"일 때 하나를 골라야 한다. 이때 보는 기준이 다르다.

| 명령 | 동률일 때 기준 | 이유 |
|---|---|---|
| `log` | **만든 순서** (`seq`가 작은 쪽 먼저) | 위상 정렬이 후보를 `nodes`(= 생성 순서 리스트)에서 앞선 것부터 꺼낸다 |
| `ancestors` | **해시 사전순** (같은 거리 안에서) | 같은 층의 조상을 해시 오름차순으로 정렬한다 |
| `path` | **해시 사전순** (경로 문자열이 가장 작은 것) | 미션이 "경로 문자열 사전순 최소"로 정했다 |

즉 **`log`만 만든 순서**를 보고, **`path`와 `ancestors`는 해시**를 본다.
타임스탬프는 이 세 명령의 동률 처리에 쓰이지 않는다. (`log --sort-by=date`만 타임스탬프를 쓴다.)

## 실제로 확인한 예: 만든 순서와 해시 순서가 다를 때

두 기준이 다른 결과를 내는 경우를 일부러 골라 실행했다. 해시는 실행마다 달라진다.

```
init "Alice"
commit "A"           → 1abd9c9
branch side
commit "B"           → fef3dac     ← B를 먼저 만들었다
switch side
commit "C"           → 865883a     ← C를 나중에 만들었다
switch main
merge side           → 94a32a2     (D: 병합 커밋)
commit "E"           → 24b0d02
```

```
A(1abd9c9) ─ B(fef3dac) ─┐
      └──── C(865883a) ──┴─ D(94a32a2) ─ E(24b0d02)
```

해시를 비교하면 `865883a`(C) < `fef3dac`(B)다. `8` < `f`이므로 **해시로는 C가 더 작고, 만든 순서로는 B가 먼저**다.

### log — 만든 순서

```
log
commit 1abd9c9 (Alice, …)
    A
commit fef3dac (Alice, …)
    B                          ← B가 먼저 (먼저 만들었으므로)
commit 865883a (Alice, …) [side]
    C
commit 94a32a2 (Alice, …) merge: fef3dac 865883a
    Merge branch 'side' into main
commit 24b0d02 (Alice, …) [HEAD -> main]
    E
```

`B`와 `C`는 서로 제약이 없다. 이럴 때는 **먼저 만든 B가 앞**에 온다. 해시가 더 큰 `fef3dac`인데도 그렇다.
`D`는 두 부모가 모두 나온 뒤에 오고, `E`는 마지막이다.

### ancestors — 해시 사전순

```
ancestors 24b0d02
Ancestors of 24b0d02 (4):
- 94a32a2: Merge branch 'side' into main      ← 거리 1
- 865883a: C                                  ← 거리 2, 해시가 더 작은 쪽이 먼저
- fef3dac: B                                  ← 거리 2
- 1abd9c9: A                                  ← 거리 3
```

`B`와 `C`는 같은 거리(2)다. 이번에는 **해시가 작은 C가 먼저** 나온다. `log`와 순서가 반대다.

### path — 해시 사전순

```
path 1abd9c9 24b0d02
Path: 1abd9c9 -> 865883a -> 94a32a2 -> 24b0d02

path 24b0d02 1abd9c9
Path: 24b0d02 -> 94a32a2 -> 865883a -> 1abd9c9
```

`A`에서 `E`까지 `B` 경유와 `C` 경유가 길이 4로 같다. 해시가 작은 `865883a`(C) 쪽이 선택된다.
방향을 바꿔도 같은 쪽을 지난다.

### 한눈에 비교

| | B가 먼저? C가 먼저? | 보는 값 |
|---|---|---|
| `log` | **B** | 만든 순서 (B가 먼저 만들어짐) |
| `ancestors` | **C** | 해시 (`865883a` < `fef3dac`) |
| `path` | **C 경유** | 해시 (`865883a` < `fef3dac`) |

## 만든 순서(seq)는 어디에 저장되나

- 각 `Commit` 객체의 **`seq` 필드**에 저장된다. (`mini_git/models.py`)
- 커밋을 만들 때 `seq = len(self._order) + 1`로 정한다. 첫 커밋이 1, 그다음 2, 3, …
- 만든 순서대로 해시를 담는 `_order` 리스트가 따로 있고, `log`는 이 리스트를 위상 정렬에 넘긴다.
- 타임스탬프를 쓰지 않는 이유: 같은 초에 여러 커밋이 만들어질 수 있어 동률이 많고, 시계가 뒤로 가면 순서가 틀어진다. `seq`는 중복이 없고 항상 늘어난다.
- 모두 메모리에만 있어서 프로그램을 종료하면 사라진다.

## 기억법

> `log` 는 **먼저 만든 쪽이 먼저**, `path` 와 `ancestors` 는 **해시가 작은 쪽이 먼저**.
