#!/bin/bash
# Mini Git 데모: 명령어를 자동으로 입력하고 결과를 보여 준다.
# 사용법: ./test.sh        (다른 파이썬: PYTHON=python3.11 ./test.sh)
# 해시는 실행마다 달라지므로, 커밋 출력에서 읽어 path/ancestors 명령에 자동으로 채운다.
#
# 이 스크립트로 확인할 수 있는 것
#   [1] 기본 흐름   : init/commit/branch/switch/log/path/search/ancestors/정렬이 미션 예시대로 동작
#                     (log에서 부모가 먼저 나오는지, 브랜치 라벨이 붙는지)
#   [2] merge       : 부모가 둘인 병합 커밋, PATH 동률일 때 해시가 사전순으로 작은 쪽 선택,
#                     ANCESTORS의 거리순·해시순 출력과 중복 없음
#   [3] merge 상태  : fast-forward / Already up to date / Unknown branch
#   [4] 경로 없음   : 서로 연결되지 않은 두 루트 사이의 PATH → No path
#   [5] USER        : 작성자가 섞였을 때 --sort-by=author가 실제로 순서를 바꾸는지,
#                     SEARCH --author가 사람별로 다른 결과를 내는지
#   [6] 에러/경계   : INIT 전 차단, 대소문자 규칙, 따옴표, 잘못된 인자, 없는 커밋·브랜치
# 확인하지 않는 것: 프롬프트·EOF·Ctrl-C 같은 REPL 동작(→ unittest), 해시 유일성 충돌 처리(→ unittest)

cd "$(dirname "$0")" || exit 1
PYTHON="${PYTHON:-/usr/local/bin/python3.12}"

"$PYTHON" - <<'EOF'
import re
import sys

from mini_git.cli import execute
from mini_git.repository import Repository

HASH = re.compile(r"\[\S+ ([0-9a-f]{7})\]")


def section(title, check, steps):
    """check: 이 섹션에서 무엇을 보면 되는지 한 줄 설명.
    steps: 문자열 명령 또는 (명령, 저장이름). 저장이름이 있으면 출력의 해시를 {이름}으로 쓸 수 있다."""
    print(f"\n{'=' * 60}\n{title}\n  확인: {check}\n{'=' * 60}")
    repo = Repository()
    saved = {}
    for step in steps:
        cmd, name = step if isinstance(step, tuple) else (step, None)
        if cmd.startswith("#"):  # 설명 줄은 실행하지 않고 그대로 보여 준다
            print(cmd)
            continue
        cmd = cmd.format(**saved)
        out = execute(repo, cmd)
        print(f"mini-git> {cmd}")
        if out:
            print(out)
        match = HASH.match(out)
        if name and match:
            saved[name] = match.group(1)


section("[1] 기본 흐름 (미션 예시)",
        "log에서 부모가 먼저 나오고 브랜치 라벨이 붙는다. path·search·ancestors·정렬이 동작한다", [
    'init "Alice"',
    ('commit "Initial commit"', "c1"),
    "branch feature",
    "switch feature",
    ('commit "Add login feature"', "c2"),
    "switch main",
    ('commit "Add payment feature"', "c3"),
    "log",
    "path {c1} {c3}",
    "path {c2} {c3}",
    'search "login"',
    "search --author=Alice",
    "ancestors {c3}",
    "log --sort-by=date",
    "log --sort-by=author",
])

section("[2] merge로 다이아몬드 만들기 + PATH 사전순 동률",
        "병합 커밋에 merge: 부모 둘이 표시되고, path가 m1·f1 중 해시가 작은 쪽을 지난다", [
    'init "Alice"',
    ('commit "root"', "root"),
    "branch f",
    ('commit "m1"', "m1"),
    "switch f",
    ('commit "f1"', "f1"),
    "switch main",
    ('merge f', "merge"),
    "log",
    "path {root} {merge}",
    "path {merge} {root}",
    "ancestors {merge}",
    "# 위 path는 m1, f1 중 해시가 사전순으로 더 작은 쪽을 지난다",
])

section("[3] merge 상태 3가지",
        "Fast-forward → Already up to date → Unknown branch 순으로 나온다", [
    'init "Alice"',
    'commit "root"',
    "branch feature",
    "switch feature",
    'commit "on feature"',
    "switch main",
    "merge feature",
    "merge feature",
    "merge nope",
])

section("[4] 경로 없음 (루트가 둘)",
        "연결되지 않은 두 커밋은 No path", [
    'init "Alice"',
    "branch orphan",
    ('commit "on main"', "a"),
    "switch orphan",
    ('commit "on orphan"', "b"),
    "path {a} {b}",
])

section("[5] USER로 작성자를 바꿔 정렬·검색 확인",
        "log는 생성 순서, --sort-by=author는 Alice가 먼저. search --author가 사람별로 다르다", [
    'init "Bob"',
    'commit "b1"',
    'user "Alice"',
    'commit "a1"',
    'user "Bob"',
    'commit "b2"',
    "log",
    "log --sort-by=author",
    "search --author=Alice",
    "search --author=Bob",
    "# log는 생성 순서(b1, a1, b2), --sort-by=author는 Alice가 먼저(a1, b1, b2)",
])

section("[6] 에러와 경계 입력",
        "INIT 전 차단, 대소문자 규칙, 따옴표, Invalid args·Unknown ... 메시지", [
    "log",
    'commit "x"',
    "hello",
    'INIT "Alice Kim"',
    "init Bob",
    "log",
    ('commit "Add login feature"', "c1"),
    'Commit "Fix LOGIN bug"',
    "switch nope",
    "switch main",
    "branch main",
    "path onlyone",
    "path {c1} zzz",
    "ancestors zzz",
    "ancestors {c1}",
    "commit Add login",
    'commit "unterminated',
    "log --sort-by=size",
    "LOG --SORT-BY=Date",
    "search --author=\"Alice Kim\"",
    "search --author=alice",
    "search --author=",
    "search LOGIN",
    'search "add login"',
    "search nothing",
    "log extra",
    "quit",
])
EOF
