# Mini Git — 커밋 DAG · 역색인 · 직접 구현한 정렬 (b5-2)

> Git의 커밋 구조를 **그래프 · 역색인 · 정렬**로 직접 풀어 본 CLI 프로그램.
> 외부 라이브러리 없이 **표준 라이브러리만** 쓰고, `sorted()`·`list.sort()`는 쓰지 않았다.

| | |
|---|---|
| 실행 | `python main.py` (`python -m mini_git`도 같다) |
| 개발 환경 | Python 3.10 이상 (검증: 3.13.11 · 3.12.3, Linux) |
| 외부 라이브러리 | **없음** (`hashlib`, `shlex`, `datetime`, `collections.deque`) |
| 저장 방식 | 메모리 (프로세스를 끝내면 사라진다. 영속성은 미션 범위 밖) |
| 핵심 알고리즘 | Kahn 위상 정렬 · 무방향 BFS 최단 경로 · 조상 BFS · 병합 정렬 · 역색인 |
| 테스트 | `unittest` 63개 |

설계 결정은 [PLAN.md](PLAN.md)에 있다.

---

## 목차

1. [실행 방법](#실행-방법)
2. [명령](#명령)
3. [출력 형식](#출력-형식)
4. [미션 예시 시나리오 — 실제 실행 결과](#미션-예시-시나리오--실제-실행-결과)
5. [에러 표준과 경계 입력 — 실제 실행 결과](#에러-표준과-경계-입력--실제-실행-결과)
6. [동작 원리 요약](#동작-원리-요약)
7. [폴더 구조](#폴더-구조)
8. [요구사항 체크리스트](#요구사항-체크리스트)
9. [검증](#검증)
10. [알아 둘 점](#알아-둘-점)

---

## 실행 방법

설치 과정이 없다. Python 3.10 이상이면 내려받아 바로 실행한다.

```bash
git clone https://github.com/rlawnsxo8709/b5-2.git
cd b5-2
python3 main.py
```

`mini-git> ` 프롬프트가 뜨면 명령을 입력한다. `exit` 또는 `quit`으로 끝내고, 입력이 끝나는 EOF(Ctrl-D)나 Ctrl-C에서도 트레이스백 없이 줄바꿈 후 정상 종료한다(종료 코드 0).
빈 줄은 무시한다. 파이프로도 실행할 수 있다.

```bash
printf 'init "Alice"\ncommit "Initial commit"\nlog\nexit\n' | python3 main.py
```

## 명령

| 명령 | 형식 | 동작 |
|---|---|---|
| `INIT` | `INIT <user_name>` | 저장소를 초기화한다. `main` 브랜치와 HEAD, 현재 사용자(author)를 설정한다. 저장소당 1회 |
| `BRANCH` | `BRANCH <branch_name>` | 현재 HEAD 커밋을 가리키는 새 브랜치를 만든다 |
| `SWITCH` | `SWITCH <branch_name>` | HEAD를 지정한 브랜치로 옮긴다 |
| `COMMIT` | `COMMIT <message>` | 현재 HEAD를 부모로 하는 새 커밋을 만들고 역색인을 갱신한다 |
| `LOG` | `LOG` | 모든 커밋을 **부모가 먼저** 나오는 위상 순서로 출력한다 |
| `LOG` | `LOG --sort-by=date\|author` | 병합 정렬로 정렬해 출력한다. 동률은 생성 순서(seq)로 가른다 |
| `PATH` | `PATH <commit1> <commit2>` | 부모-자식을 무방향 간선으로 본 최단 경로. 동률이면 `h1->h2->...` 사전순 최소. 없으면 `No path` |
| `ANCESTORS` | `ANCESTORS <commit_hash>` | 도달 가능한 모든 조상을 가까운 순으로 출력한다 |
| `SEARCH` | `SEARCH <keyword>` | 메시지에 키워드가 든 커밋(역색인). 키워드가 여러 개면 모두 든 커밋(교집합) |
| `SEARCH` | `SEARCH --author=<name>` | 해당 작성자의 커밋(역색인) |
| `EXIT` / `QUIT` | | `Bye`를 출력하고 종료한다 |

**입력 규칙**

- 명령명은 대소문자를 구분하지 않는다. (`INIT`, `init`, `Init` 모두 같다)
- 공백이 든 인자는 따옴표로 감싼다. (`COMMIT "Add login feature"`, `SEARCH --author="Alice Kim"`) 파싱은 `shlex.split`이다.
- 따옴표 없이 단어를 여러 개 쓰면 인자가 여러 개로 나뉘므로 `Invalid args`다. (`COMMIT Add login` → `Invalid args`)
- 옵션은 `--author=<name>`, `--sort-by=date|author` 형식만 받는다. 옵션 이름과 값(`date`, `author`)은 **소문자로 정확히** 써야 하고, 작성자 이름은 대소문자를 구분한다.

## 출력 형식

| 명령 | 출력 |
|---|---|
| `init "Alice"` | `Initialized repository.` / `Current branch: main` / `Current user: Alice` (3줄) |
| `commit "msg"` | `[main a1b2c3d] msg` — 현재 브랜치와 7자리 해시 |
| `branch feature` | `Created branch: feature` |
| `switch feature` | `Switched to branch: feature` (이미 그 브랜치면 `Already on branch: feature`) |
| `log` | 커밋마다 2줄: `commit <hash> (<author>, <YYYY-MM-DD HH:MM:SS>) [<브랜치>]` 다음 줄에 `    <message>` |
| `path a b` | `Path: a -> b -> c` 또는 `No path` (같은 커밋이면 `Path: a`) |
| `ancestors h` | `Ancestors of <h> (N):` 다음에 `- <hash>: <message>` 줄들. 없으면 `No ancestors of <h>` |
| `search login` | `Found N commit(s):` 다음에 `- <hash>: <message>` 줄들. 없으면 `No commits found` |
| `exit` | `Bye` |

`log`의 브랜치 라벨은 그 커밋을 **지금 가리키고 있는** 브랜치다. HEAD 브랜치는 `HEAD -> main`으로 맨 앞에 쓰고, 여러 개면 `[HEAD -> main, feature]`처럼 쉼표로 잇는다. 가리키는 브랜치가 없으면 `[...]`를 생략한다.
커밋이 하나도 없으면 `No commits yet`을 출력한다.

## 미션 예시 시나리오 — 실제 실행 결과

아래는 미션 문서의 결과 예시와 같은 순서의 명령을 `python main.py`에 **파이프로 넣어 실제로 실행한 출력**이다.
해시는 커밋 시각에 따라 실행마다 달라지므로, `path`·`ancestors`에 쓸 해시는 앞선 `commit` 출력에서 읽어 이어서 입력했다(스크립트로 프로세스를 구동). 파이프 입력은 화면에 에코되지 않으므로, 읽기 쉽도록 프롬프트 뒤에 **입력한 명령**을 함께 적었고 나머지는 프로그램이 낸 출력 그대로다. 종료 코드는 0이고 stderr는 비어 있었다.

```
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice
mini-git> commit "Initial commit"
[main 8d9c106] Initial commit
mini-git> branch feature
Created branch: feature
mini-git> switch feature
Switched to branch: feature
mini-git> commit "Add login feature"
[feature 10f8cd4] Add login feature
mini-git> switch main
Switched to branch: main
mini-git> commit "Add payment feature"
[main 7e3d35d] Add payment feature
mini-git> log
commit 8d9c106 (Alice, 2026-10-04 04:39:41)
    Initial commit
commit 10f8cd4 (Alice, 2026-10-04 04:39:41) [feature]
    Add login feature
commit 7e3d35d (Alice, 2026-10-04 04:39:41) [HEAD -> main]
    Add payment feature
mini-git> path 8d9c106 7e3d35d
Path: 8d9c106 -> 7e3d35d
mini-git> path 10f8cd4 7e3d35d
Path: 10f8cd4 -> 8d9c106 -> 7e3d35d
mini-git> search "login"
Found 1 commit(s):
- 10f8cd4: Add login feature
mini-git> ancestors 7e3d35d
Ancestors of 7e3d35d (1):
- 8d9c106: Initial commit
mini-git> log --sort-by=author
commit 8d9c106 (Alice, 2026-10-04 04:39:41)
    Initial commit
commit 10f8cd4 (Alice, 2026-10-04 04:39:41) [feature]
    Add login feature
commit 7e3d35d (Alice, 2026-10-04 04:39:41) [HEAD -> main]
    Add payment feature
mini-git> log --sort-by=date
commit 8d9c106 (Alice, 2026-10-04 04:39:41)
    Initial commit
commit 10f8cd4 (Alice, 2026-10-04 04:39:41) [feature]
    Add login feature
commit 7e3d35d (Alice, 2026-10-04 04:39:41) [HEAD -> main]
    Add payment feature
mini-git> exit
Bye
```

- `log`: `Initial commit`이 두 브랜치의 공통 조상이라 가장 먼저 나온다. `feature`가 가리키는 커밋에는 `[feature]`, HEAD인 `main`에는 `[HEAD -> main]`이 붙는다. 첫 커밋은 이제 어떤 브랜치도 가리키지 않아 라벨이 없다.
- `path <feature 커밋> <main 커밋>`: 두 커밋이 형제라서 공통 부모를 거쳐 `feature -> Initial -> main`으로 간다. 부모 방향만 따라갔다면 길이 없었을 것이다.
- 세 커밋의 작성자가 모두 같아서 `--sort-by=author`는 동률이고, 생성 순서(seq)로 정렬된다. 작성자가 섞인 경우의 정렬은 단위 테스트에서 검증한다([알아 둘 점](#알아-둘-점) 참고).

순수 파이프 입력(해시가 필요한 명령 없이)만으로 실행한 결과는 다음과 같다. 프롬프트와 출력이 한 줄에 이어 붙는 것이 파이프 실행의 실제 모습이다.

```
$ printf 'init "Alice"\ncommit "Initial commit"\nbranch feature\nswitch feature\ncommit "Add login feature"\nswitch main\ncommit "Add payment feature"\nlog\nsearch "login"\nexit\n' | python3 main.py
mini-git> Initialized repository.
Current branch: main
Current user: Alice
mini-git> [main 3423104] Initial commit
mini-git> Created branch: feature
mini-git> Switched to branch: feature
mini-git> [feature 2460f18] Add login feature
mini-git> Switched to branch: main
mini-git> [main 15ad94e] Add payment feature
mini-git> commit 3423104 (Alice, 2026-10-04 04:39:54)
    Initial commit
commit 2460f18 (Alice, 2026-10-04 04:39:54) [feature]
    Add login feature
commit 15ad94e (Alice, 2026-10-04 04:39:54) [HEAD -> main]
    Add payment feature
mini-git> Found 1 commit(s):
- 2460f18: Add login feature
mini-git> Bye
```

## 에러 표준과 경계 입력 — 실제 실행 결과

| 상황 | 출력 |
|---|---|
| 인자 개수·형식 오류, 따옴표 미닫힘, 옵션 값 오류 | `Invalid args` |
| 없는 브랜치 | `Unknown branch: <name>` |
| 없는 커밋 | `Unknown commit: <hash>` |
| 알 수 없는 명령 | `Unknown command: <cmd>` |
| `INIT` 전에 다른 명령 | `Repository not initialized. Use INIT <user_name>` |
| `INIT` 두 번째 | `Repository already initialized` |
| 이미 있는 브랜치 | `Branch already exists: <name>` |
| 연결이 없는 두 커밋 | `No path` |

어떤 오류도 프로그램을 멈추지 않는다. 모두 한 줄 메시지로 출력되고 프롬프트로 돌아온다.
아래는 `INIT` 전 명령, 공백이 든 따옴표 인자, 대소문자 규칙, 각종 오류를 한 세션에 모아 실제로 실행한 결과다(입력 표기는 위와 같다).

```
mini-git> log
Repository not initialized. Use INIT <user_name>
mini-git> commit "x"
Repository not initialized. Use INIT <user_name>
mini-git> hello
Unknown command: hello
mini-git> init "Alice Kim"
Initialized repository.
Current branch: main
Current user: Alice Kim
mini-git> init Bob
Repository already initialized
mini-git> log
No commits yet
mini-git> commit "Add login feature"
[main 87e145b] Add login feature
mini-git> Commit "Fix LOGIN bug"
[main f6b6a0c] Fix LOGIN bug
mini-git> switch nope
Unknown branch: nope
mini-git> switch main
Already on branch: main
mini-git> branch main
Branch already exists: main
mini-git> path onlyone
Invalid args
mini-git> path 87e145b zzz
Unknown commit: zzz
mini-git> path f6b6a0c f6b6a0c
Path: f6b6a0c
mini-git> commit "unterminated
Invalid args
mini-git> commit Add login
Invalid args
mini-git> ancestors zzz
Unknown commit: zzz
mini-git> ancestors 87e145b
No ancestors of 87e145b
mini-git> Log --SORT-BY=Date
Invalid args
mini-git> log --sort-by=size
Invalid args
mini-git> search --author="Alice Kim"
Found 2 commit(s):
- 87e145b: Add login feature
- f6b6a0c: Fix LOGIN bug
mini-git> search --author=alice
No commits found
mini-git> search LOGIN
Found 2 commit(s):
- 87e145b: Add login feature
- f6b6a0c: Fix LOGIN bug
mini-git> search "add login"
Found 1 commit(s):
- 87e145b: Add login feature
mini-git> search nothing
No commits found
mini-git> quit
Bye
```

첫 커밋 전에 `BRANCH`로 만든 브랜치는 부모가 없는 **새 루트**가 된다. 이때 두 루트 사이에는 길이 없어 `No path`가 실제로 나온다.

```
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice
mini-git> branch orphan
Created branch: orphan
mini-git> commit "on main"
[main 4b14866] on main
mini-git> switch orphan
Switched to branch: orphan
mini-git> commit "on orphan"
[orphan df37c39] on orphan
mini-git> path 4b14866 df37c39
No path
mini-git> log
commit 4b14866 (Alice, 2026-10-04 04:39:41) [main]
    on main
commit df37c39 (Alice, 2026-10-04 04:39:41) [HEAD -> orphan]
    on orphan
mini-git> exit
Bye
```

## 동작 원리 요약

| 기능 | 알고리즘 · 자료구조 | 코드 |
|---|---|---|
| 커밋 저장소 | `dict[hash → Commit]`, 해시로 O(1) 조회 | `mini_git/repository.py:44` |
| 해시 | `sha1(seq\|author\|message\|timestamp\|salt)` 앞 7자리. 이미 있으면 salt를 올려 다시 해시해 **길이 7 고정** | `mini_git/repository.py:173` |
| LOG | Kahn 위상 정렬. 꺼낼 수 있는 노드가 여럿이면 생성 순서(seq) 우선. 사이클이면 `ValueError` | `mini_git/graph.py:12` |
| PATH | 도착지에서 BFS로 거리를 구하고, 출발지에서 거리가 1씩 줄어드는 이웃 중 해시가 가장 작은 쪽을 고른다 | `mini_git/graph.py:53` |
| ANCESTORS | 부모 방향 BFS. 가까운 조상부터, 같은 거리면 해시 오름차순. 방문 집합으로 중복 제거 | `mini_git/graph.py:85` |
| 정렬 | 안정 병합 정렬, 평균·최악 O(n log n). `key`로 날짜·작성자 기준 전환, 키 끝에 seq를 붙여 동률 처리 | `mini_git/sorting.py:4`, `mini_git/repository.py:20` |
| 역색인 | `dict[keyword → [hash]]`, `dict[author → [hash]]`. 커밋 시점에 갱신, 검색은 토큰별 목록의 교집합 | `mini_git/index.py:16` |

## 폴더 구조

```
.
├── main.py                  `python main.py` 진입점
├── mini_git/
│   ├── models.py            Commit (frozen dataclass)
│   ├── errors.py            MiniGitError — str(e)가 곧 사용자 메시지
│   ├── sorting.py           merge_sort
│   ├── graph.py             topo_order · shortest_path · ancestors (순수 함수)
│   ├── index.py             tokenize · InvertedIndex
│   ├── repository.py        상태 소유: 저장소·브랜치·HEAD·사용자·자식 목록
│   ├── cli.py               파싱·분기·출력, REPL
│   └── __main__.py          `python -m mini_git`
├── tests/                   unittest 63개 (단위 · CLI/REPL · 제약 준수 AST 검사)
└── README.md  PLAN.md
```

알고리즘 모듈(`graph.py`, `sorting.py`, `index.py`)은 저장소 상태를 모르는 독립 함수·클래스이고, `repository.py`가 상태를 소유하며, `cli.py`는 문자열을 해석해 `Repository`를 호출하고 결과를 문자열로 바꾸기만 한다.

## 요구사항 체크리스트

**CLI 공통 규칙**

- [x] 명령어 대소문자 무시 — `mini_git/cli.py:138` (`tokens[0].lower()`) · `tests/test_cli.py` `test_command_name_is_case_insensitive_but_options_are_not`
- [x] 공백 포함 문자열 인자는 따옴표로 감싸 하나의 인자로 처리 — `mini_git/cli.py:138` (`shlex.split`) · `test_quoted_arguments_are_single_arguments`, `test_author_search_and_sort`
- [x] 옵션 표기 `--author=<name>`, `--sort-by=date|author` — `mini_git/cli.py:73`, `mini_git/cli.py:101`
- [x] 표준 에러 `Invalid args` / `Unknown branch: <name>` / `Unknown commit: <hash>` — `mini_git/repository.py`, `mini_git/cli.py` · `test_errors`

**커밋 그래프**

- [x] 커밋 노드 필드 `hash`, `message`, `author`, `timestamp`, `parents` (+ `seq`) — `mini_git/models.py:8`
- [x] 부모 0개 이상(첫 커밋·새 루트는 빈 튜플) — `mini_git/repository.py:90` · `test_branch_before_first_commit_creates_disconnected_root`
- [x] DAG: 새 커밋은 이미 존재하는 커밋만 부모로 삼고, 사이클이면 위상 정렬이 `ValueError` — `mini_git/graph.py:12` · `test_topo_cycle_raises`
- [x] 해시맵 기반 조회 — `mini_git/repository.py:116` (`dict`)
- [x] 해시 세션 내 유일, 길이 7 고정 — `mini_git/repository.py:173` · `test_hash_unique_fixed_length_even_with_collisions`, `test_hashes_stay_unique_and_fixed_length_in_a_burst`

**역색인**

- [x] 검색이 전체 커밋을 순회하지 않음 — `mini_git/index.py:34`
- [x] 키워드 = `split()` 후 `lower()` 토큰 — `mini_git/index.py:4` · `test_tokenize`
- [x] `keyword → hash 목록`, `author → hash 목록` 2종 — `mini_git/index.py:24`
- [x] 커밋 시점에 갱신 — `mini_git/repository.py:90` (`add_commit` 호출)

**정렬**

- [x] `sorted()`, `list.sort()` 미사용, 직접 구현 병합 정렬 — `mini_git/sorting.py:4` · `tests/test_constraints.py`(AST 검사)
- [x] 비교 기준 변경(날짜·작성자) — `mini_git/repository.py:20` · `test_log_sorted_date_and_invalid_key`, `test_log_sorted_by_author_ties_by_seq`

**명령**

- [x] `INIT`: 저장소 초기화, `main` 브랜치·HEAD·사용자 설정 — `mini_git/repository.py:63` · `test_init_sets_main_head_user`
- [x] `BRANCH`: 현재 HEAD를 가리키는 새 브랜치 — `mini_git/repository.py:74` · `test_commit_moves_only_current_branch`
- [x] `SWITCH`: HEAD 이동 — `mini_git/repository.py:83` · `test_branch_switch_commit_flow`
- [x] `COMMIT`: HEAD를 부모로 새 커밋, 역색인 갱신 — `mini_git/repository.py:90`
- [x] `LOG`: 부모가 항상 먼저 — `mini_git/graph.py:12` · `test_topo_parents_first`, `test_log_is_parent_first_across_branches`
- [x] `LOG --sort-by=date|author` — `mini_git/repository.py:129` · `test_author_search_and_sort`
- [x] `PATH`: 무방향 최단 경로, 사전순 최소, 없으면 `No path` — `mini_git/graph.py:53` · `test_lexicographic_tie_break`, `test_no_path_between_disconnected_roots`, `test_same_commit_path`
- [x] `ANCESTORS`: 모든 조상 — `mini_git/graph.py:85` · `test_ancestors`, `test_ancestors_diamond_has_no_duplicates_and_orders_ties_by_hash`
- [x] `SEARCH <keyword>`, `SEARCH --author=<name>` — `mini_git/index.py:34`, `mini_git/index.py:51` · `test_multi_token_intersection`, `test_search_edge_cases`

**REPL · 제출물**

- [x] `mini-git> ` 프롬프트에서 명령을 반복 입력, `exit`/`quit` 종료(EOF·Ctrl-C도 정상 종료) — `mini_git/cli.py:169` · `TestRepl`
- [x] 엔트리 포인트 `main.py` 1개 + `README.md` 1개 — `python main.py`

**제약 사항**

- [x] 그래프 전용 라이브러리 미사용, 정렬 API 미사용 — `tests/test_constraints.py`가 `mini_git/*.py`, `main.py`, `tests/*.py`를 AST로 검사
- [x] 알고리즘 로직을 독립 함수·클래스로 분리 — `graph.py`, `sorting.py`, `index.py`
- [x] 주요 함수·클래스에 docstring
- [x] 파일 내용 추적·네트워크·영속성 미구현(커밋 메타데이터 중심, 메모리 동작)
- [x] 보너스(diff, merge, 정렬 성능 비교)는 구현하지 않음

## 검증

```bash
python3 -m unittest discover -s tests -t . -v
```

실행 결과(마지막 3줄):

```
Ran 63 tests in 0.070s

OK
```

| 파일 | 개수 | 검사 대상 |
|---|---|---|
| `test_sorting.py` | 6 | 숫자·빈 입력·`key`·**안정성**·입력 비변경·복합 키·500개 입력의 정렬 순서와 구성 |
| `test_graph.py` | 9 | 부모 우선 위상 순서, 입력이 생성 순서가 아닌 경우, 사이클, 최단 경로, 사전순 동률, 연결 없음, 조상(합류 지점 중복 없음) |
| `test_index.py` | 6 | 토큰화, 대소문자 무시, 다중 토큰 교집합, 존재하지 않는 토큰, 작성자 정확 일치 |
| `test_repository.py` | 17 | INIT 전 모든 연산 차단, 브랜치·커밋 흐름, 해시 충돌 주입, 같은 초 커밋의 seq 정렬, 시계가 뒤로 간 경우, 연결 없는 두 루트 |
| `test_cli.py` | 22 | 출력 형식 전체, 따옴표 인자, INIT 전 안내, 에러 표준, 옵션 대소문자 규칙, 라벨, REPL 세션(프로세스 실행 포함)·EOF·종료·Ctrl-C |
| `test_constraints.py` | 3 | AST 검사: `sorted`·`.sort`·`heapq`·`bisect`·`networkx`·`graphlib`·외부 import 0건, 검사기 자체가 위반을 잡는지 |

테스트는 mock을 쓰지 않는다. 시간과 해시 충돌만 `Repository(clock=..., hash_func=...)`로 주입하고, REPL은 실제 `main.py` 프로세스를 실행해 검증한다.
테스트 코드에서도 `sorted`·`.sort`를 쓰지 않는다(기대값은 리터럴로 쓴다).

## 알아 둘 점

- **`--sort-by=author`의 다중 작성자**: `INIT`은 저장소당 한 번이고 사용자를 바꾸는 명령이 미션에 없다. 그래서 CLI 세션에서는 작성자가 한 명뿐이다. 여러 작성자가 섞인 정렬은 `Repository.user`를 직접 바꾸는 단위 테스트(`test_log_sorted_by_author_ties_by_seq`, `test_author_search_and_sort`)로 검증했다.
- **`LOG` 순서와 생성 순서**: 커밋의 부모는 항상 먼저 만들어졌으므로 위상 순서는 지금 구조에서 생성 순서와 같게 나온다. 그래도 Kahn 알고리즘으로 "부모 우선"과 사이클 검출을 알고리즘이 직접 보장하게 했다.
- **실제 그래프 모양**: `Commit.parents`는 0개 이상을 담지만 merge(보너스)를 구현하지 않아 CLI가 만드는 커밋은 부모가 0~1개다. 그래서 CLI 세션의 그래프는 트리(루트가 여럿이면 숲)이고, 부모가 둘인 합류 지점이 필요한 동작(PATH의 사전순 동률, ANCESTORS의 다이아몬드 중복 제거)은 손으로 만든 그래프를 쓰는 단위 테스트(`tests/test_graph.py`)로만 검증된다.
- **`SEARCH`의 `--`로 시작하는 키워드**: `--author=<name>` 외의 `--xxx`는 옵션 오류(`Invalid args`)로 본다.
- **`SEARCH` 다중 단어**: `SEARCH "add login"`은 `add`와 `login`이 **모두** 든 커밋(교집합)이다.
- **해시 공간**: 7자리 16진수(약 2.7억 가지)다. 충돌은 salt를 올려 다시 해시하므로 유일성은 항상 보장되지만, 커밋이 매우 많아지면 재해시가 늘어난다.
- 데이터는 메모리에만 있다. 프로세스가 끝나면 저장소도 사라진다.
