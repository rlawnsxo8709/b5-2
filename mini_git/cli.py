"""CLI(REPL): 입력 줄을 해석해 Repository를 호출하고 결과를 문자열로 만든다.

이 모듈은 파싱, 명령 분기, 출력 형식만 맡는다. 상태와 알고리즘은 다른 모듈에 있다.
"""

import shlex
import sys

from mini_git.errors import MiniGitError
from mini_git.repository import Repository

PROMPT = "mini-git> "
EXIT_COMMANDS = ("exit", "quit")
INVALID_ARGS = "Invalid args"
SORT_BY_PREFIX = "--sort-by="
AUTHOR_PREFIX = "--author="
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _expect(args, count):
    """인자가 정확히 count개가 아니면 Invalid args."""
    if len(args) != count:
        raise MiniGitError(INVALID_ARGS)
    return args


def _labels(repo, commit_hash):
    """커밋을 가리키는 브랜치 라벨. HEAD 브랜치는 `HEAD -> 이름`으로 맨 앞에 둔다."""
    names = repo.branches_at(commit_hash)
    head = [f"HEAD -> {n}" for n in names if n == repo.current_branch]
    rest = [n for n in names if n != repo.current_branch]
    return head + rest


def _format_log_entry(repo, commit):
    header = f"commit {commit.hash} ({commit.author}, {commit.timestamp.strftime(TIME_FORMAT)})"
    if len(commit.parents) > 1:
        header += f" merge: {' '.join(commit.parents)}"
    labels = _labels(repo, commit.hash)
    if labels:
        header += f" [{', '.join(labels)}]"
    return f"{header}\n    {commit.message}"


def _format_hits(commits):
    return "\n".join(f"- {c.hash}: {c.message}" for c in commits)


def _init(repo, args):
    (user,) = _expect(args, 1)
    repo.init(user)
    return f"Initialized repository.\nCurrent branch: {repo.current_branch}\nCurrent user: {repo.user}"


def _commit(repo, args):
    (message,) = _expect(args, 1)
    commit = repo.commit(message)
    return f"[{repo.current_branch} {commit.hash}] {commit.message}"


def _branch(repo, args):
    (name,) = _expect(args, 1)
    repo.branch(name)
    return f"Created branch: {name}"


def _switch(repo, args):
    (name,) = _expect(args, 1)
    if repo.initialized and repo.current_branch == name:
        return f"Already on branch: {name}"
    repo.switch(name)
    return f"Switched to branch: {name}"


def _merge(repo, args):
    (name,) = _expect(args, 1)
    status, commit = repo.merge(name)
    if status == "up-to-date":
        return "Already up to date"
    if status == "fast-forward":
        return f"Fast-forward: {repo.current_branch} -> {repo.head_commit}"
    return f"[{repo.current_branch} {commit.hash}] {commit.message}"


def _log(repo, args):
    if not args:
        commits = repo.log()
    elif len(args) == 1 and args[0].startswith(SORT_BY_PREFIX):
        commits = repo.log_sorted(args[0][len(SORT_BY_PREFIX):])
    else:
        raise MiniGitError(INVALID_ARGS)
    if not commits:
        return "No commits yet"
    return "\n".join(_format_log_entry(repo, c) for c in commits)


def _path(repo, args):
    a, b = _expect(args, 2)
    found = repo.path(a, b)
    if found is None:
        return "No path"
    return "Path: " + " -> ".join(found)


def _ancestors(repo, args):
    (h,) = _expect(args, 1)
    found = repo.ancestors(h)
    if not found:
        return f"No ancestors of {h}"
    return f"Ancestors of {h} ({len(found)}):\n{_format_hits(found)}"


def _search(repo, args):
    (arg,) = _expect(args, 1)
    if arg.startswith("--"):  # 옵션은 --author=<name> 하나뿐이다
        if not arg.startswith(AUTHOR_PREFIX):
            raise MiniGitError(INVALID_ARGS)
        name = arg[len(AUTHOR_PREFIX):]
        if not name.strip():
            raise MiniGitError(INVALID_ARGS)
        commits = repo.search_author(name)
    else:
        if not arg.strip():
            raise MiniGitError(INVALID_ARGS)
        commits = repo.search_keyword(arg)
    if not commits:
        return "No commits found"
    return f"Found {len(commits)} commit(s):\n{_format_hits(commits)}"


def _exit(repo, args):
    _expect(args, 0)
    return "Bye"


COMMANDS = {
    "init": _init,
    "commit": _commit,
    "branch": _branch,
    "switch": _switch,
    "merge": _merge,
    "log": _log,
    "path": _path,
    "ancestors": _ancestors,
    "search": _search,
    "exit": _exit,
    "quit": _exit,
}


def execute(repo, line):
    """한 줄을 실행하고 출력할 문자열을 돌려준다. 빈 줄은 빈 문자열.

    shlex로 나누므로 따옴표로 감싼 인자는 공백이 있어도 하나의 인자다.
    첫 토큰(명령명)만 대소문자를 무시하고, 옵션과 그 값은 정확히 일치해야 한다.
    MiniGitError는 잡아서 메시지 문자열로 바꾸므로 REPL이 오류로 멈추지 않는다.
    """
    try:
        tokens = shlex.split(line)
    except ValueError:  # 닫히지 않은 따옴표
        return INVALID_ARGS
    if not tokens:
        return ""
    handler = COMMANDS.get(tokens[0].lower())
    if handler is None:
        return f"Unknown command: {tokens[0]}"
    try:
        return handler(repo, tokens[1:])
    except MiniGitError as error:
        return str(error)


def is_exit(line):
    """줄이 인자 없는 exit/quit이면 True."""
    try:
        tokens = shlex.split(line)
    except ValueError:
        return False
    return len(tokens) == 1 and tokens[0].lower() in EXIT_COMMANDS


def repl(stdin=sys.stdin, stdout=sys.stdout):
    """`mini-git> ` 프롬프트로 명령을 반복 실행한다.

    exit/quit(`Bye` 출력), EOF와 Ctrl-C(줄바꿈 출력)에서 종료 코드 0을 돌려준다.
    Ctrl-C(KeyboardInterrupt)는 트레이스백 대신 EOF와 같은 방식으로 끝낸다.
    """
    repo = Repository()
    try:
        while True:
            stdout.write(PROMPT)
            stdout.flush()
            line = stdin.readline()
            if line == "":  # EOF
                stdout.write("\n")
                return 0
            output = execute(repo, line)
            if output:
                stdout.write(output + "\n")
            if is_exit(line):
                return 0
    except KeyboardInterrupt:
        stdout.write("\n")
        return 0
