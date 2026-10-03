"""커밋 노드 모델."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Commit:
    """불변 커밋 노드.

    parents는 부모 해시 튜플이다. 루트 커밋은 빈 튜플이다.
    seq는 저장소 안에서 1부터 늘어나는 생성 순번으로, 부모는 항상 자식보다 작은 seq를 가진다.
    같은 초에 만든 커밋처럼 timestamp가 같을 때 순서를 가리는 기준으로도 쓴다.
    """

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple
    seq: int
