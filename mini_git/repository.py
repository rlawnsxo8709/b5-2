"""저장소 상태: 커밋 저장소 · 브랜치 · HEAD · 사용자 · 자식 목록 · 역색인.

알고리즘은 graph.py, sorting.py, index.py에 있고, 이 모듈은 상태를 소유하며
알고리즘에 필요한 함수(parents_of, neighbors)를 만들어 넘기는 역할만 한다.
"""

import hashlib
from datetime import datetime

from mini_git.errors import MiniGitError
from mini_git.graph import ancestors, shortest_path, topo_order
from mini_git.index import InvertedIndex
from mini_git.models import Commit
from mini_git.sorting import merge_sort

HASH_LENGTH = 7
NOT_INITIALIZED = "Repository not initialized. Use INIT <user_name>"

# 정렬 기준별 키. 마지막 요소 seq가 동률(같은 초, 같은 작성자)을 생성 순서로 가른다.
SORT_KEYS = {
    "date": lambda c: (c.timestamp, c.seq),
    "author": lambda c: (c.author, c.seq),
}


def default_hash(seed):
    """seed의 sha1 앞 HASH_LENGTH자리."""
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:HASH_LENGTH]


class Repository:
    """메모리 위에서 동작하는 Mini Git 저장소.

    - `_commits`: dict hash -> Commit. 해시로 O(1) 조회한다.
    - `_order`: 생성 순서의 해시 리스트. seq 오름차순이며 위상 정렬의 입력이다.
    - `_children`: dict hash -> 자식 해시 리스트. PATH의 무방향 이웃을 O(차수)에 구한다.
    - `_branches`: dict 브랜치명 -> 가리키는 해시(없으면 None). 생성 순서가 유지된다.
    - HEAD는 현재 브랜치 이름(`current_branch`)이고, 가리키는 커밋은 `head_commit`이다.

    clock은 현재 시각을 돌려주는 함수, hash_func은 seed 문자열로 7자리 해시를 만드는 함수다.
    둘 다 테스트에서 시간과 해시 충돌을 주입하려고 바꿀 수 있게 열어 두었다.
    """

    def __init__(self, clock=datetime.now, hash_func=None):
        self._clock = clock
        self._hash_func = hash_func or default_hash
        self._commits = {}
        self._order = []
        self._children = {}
        self._branches = {}
        self._index = InvertedIndex()
        self.initialized = False
        self.current_branch = None
        self.user = None

    @property
    def head_commit(self):
        """현재 브랜치가 가리키는 커밋 해시. 커밋이 없거나 초기화 전이면 None."""
        if not self.initialized:
            return None
        return self._branches[self.current_branch]

    def init(self, user):
        """저장소를 초기화한다: main 브랜치, HEAD, 현재 사용자를 설정한다."""
        if self.initialized:
            raise MiniGitError("Repository already initialized")
        if not user.strip():
            raise MiniGitError("Invalid args")
        self.initialized = True
        self.user = user
        self._branches = {"main": None}
        self.current_branch = "main"

    def set_user(self, name):
        """현재 작성자를 바꾼다. 이후 커밋부터 적용되고 기존 커밋은 그대로다."""
        self._require_init()
        if not name.strip():
            raise MiniGitError("Invalid args")
        self.user = name

    def branch(self, name):
        """현재 HEAD 커밋을 가리키는 새 브랜치를 만든다. 첫 커밋 전이면 아직 커밋이 없는 브랜치가 된다."""
        self._require_init()
        if not name.strip():
            raise MiniGitError("Invalid args")
        if name in self._branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self._branches[name] = self.head_commit

    def switch(self, name):
        """HEAD를 지정한 브랜치로 옮긴다."""
        self._require_init()
        if name not in self._branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.current_branch = name

    def commit(self, message):
        """현재 HEAD를 부모로 하는 새 커밋을 만들고 브랜치와 역색인을 갱신한다."""
        self._require_init()
        message = message.strip()
        if not message:
            raise MiniGitError("Invalid args")
        head = self.head_commit
        return self._add_commit(message, (head,) if head else ())

    def merge(self, name):
        """브랜치 name을 현재 브랜치에 합친다. (상태, 커밋) 튜플을 돌려준다.

        - "up-to-date": name의 커밋이 이미 현재 브랜치의 이력에 있거나 name에 커밋이 없다. 커밋은 None.
        - "fast-forward": 현재 브랜치가 name의 조상이다. 브랜치를 옮기기만 하고 커밋은 None.
        - "merge": 두 갈래가 갈라져 있다. 부모가 (현재 HEAD, name의 커밋) 둘인 병합 커밋을 만든다.
        """
        self._require_init()
        if name not in self._branches:
            raise MiniGitError(f"Unknown branch: {name}")
        head = self.head_commit
        target = self._branches[name]
        if target is None or target == head or (head and target in ancestors(head, self._parents_of)):
            return "up-to-date", None
        if head is None or head in ancestors(target, self._parents_of):
            self._branches[self.current_branch] = target
            return "fast-forward", None
        message = f"Merge branch '{name}' into {self.current_branch}"
        return "merge", self._add_commit(message, (head, target))

    def _add_commit(self, message, parents):
        """부모 튜플을 받아 커밋을 저장하고 브랜치·자식 목록·역색인을 갱신한다."""
        seq = len(self._order) + 1
        timestamp = self._clock()
        commit = Commit(
            hash=self._new_hash(seq, self.user, message, timestamp),
            message=message,
            author=self.user,
            timestamp=timestamp,
            parents=parents,
            seq=seq,
        )
        self._commits[commit.hash] = commit
        self._order.append(commit.hash)
        self._children[commit.hash] = []
        for parent in commit.parents:
            self._children[parent].append(commit.hash)
        self._branches[self.current_branch] = commit.hash
        self._index.add_commit(commit.hash, commit.message, commit.author)
        return commit

    def get(self, h):
        """해시로 커밋을 조회한다. 없으면 Unknown commit."""
        self._require_init()
        commit = self._commits.get(h)
        if commit is None:
            raise MiniGitError(f"Unknown commit: {h}")
        return commit

    def log(self):
        """모든 커밋을 부모가 먼저 오는 위상 순서로 돌려준다."""
        self._require_init()
        return [self._commits[h] for h in topo_order(self._order, self._parents_of)]

    def log_sorted(self, by):
        """"date" 또는 "author" 기준으로 병합 정렬한 로그. 동률은 생성 순서(seq)로 가른다."""
        self._require_init()
        if by not in SORT_KEYS:
            raise MiniGitError("Invalid args")
        return merge_sort([self._commits[h] for h in self._order], key=SORT_KEYS[by])

    def path(self, a, b):
        """두 커밋 사이의 무방향 최단 경로(해시 리스트). 연결이 없으면 None."""
        self.get(a)
        self.get(b)
        return shortest_path(a, b, self._neighbors)

    def ancestors(self, h):
        """h의 모든 조상 커밋을 BFS 순서(가까운 순)로 돌려준다."""
        self.get(h)
        return [self._commits[x] for x in ancestors(h, self._parents_of)]

    def search_keyword(self, q):
        """메시지에 q의 모든 토큰이 들어 있는 커밋(역색인 교집합), 생성 순서."""
        self._require_init()
        return [self._commits[h] for h in self._index.search_keyword(q)]

    def search_author(self, name):
        """작성자가 name과 정확히 같은 커밋, 생성 순서."""
        self._require_init()
        return [self._commits[h] for h in self._index.search_author(name)]

    def branches_at(self, h):
        """해시 h를 가리키는 브랜치 이름들(브랜치 생성 순)."""
        self._require_init()
        return [name for name, target in self._branches.items() if target == h]

    def _require_init(self):
        if not self.initialized:
            raise MiniGitError(NOT_INITIALIZED)

    def _parents_of(self, h):
        return self._commits[h].parents

    def _neighbors(self, h):
        """무방향 간선: 부모와 자식을 모두 이웃으로 본다."""
        return list(self._commits[h].parents) + self._children[h]

    def _new_hash(self, seq, author, message, timestamp):
        """sha1 앞 7자리를 만들고, 이미 있으면 salt를 올려 다시 해시해 길이를 7로 고정한다."""
        salt = 0
        while True:
            seed = f"{seq}|{author}|{message}|{timestamp.isoformat()}|{salt}"
            candidate = self._hash_func(seed)
            if candidate not in self._commits:
                return candidate
            salt += 1
