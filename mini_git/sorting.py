"""표준 정렬 API(sorted, list.sort) 없이 직접 구현한 정렬."""


def merge_sort(items, key=lambda x: x):
    """병합 정렬. 새 리스트를 돌려주고 입력은 바꾸지 않는다.

    - 안정 정렬: 키가 같으면 입력에서 앞선 원소가 앞에 온다(병합 때 왼쪽을 먼저 취한다).
    - 시간복잡도: 평균·최악 모두 O(n log n). 추가 메모리는 O(n).
    - key는 원소마다 한 번만 계산한다. 비교는 키끼리 `<`만 사용한다.
    """
    pairs = [(key(item), item) for item in items]
    return [item for _, item in _sort_pairs(pairs)]


def _sort_pairs(pairs):
    """(키, 원소) 쌍 리스트를 반으로 나눠 각각 정렬한 뒤 병합한다."""
    if len(pairs) <= 1:
        return pairs
    mid = len(pairs) // 2
    return _merge(_sort_pairs(pairs[:mid]), _sort_pairs(pairs[mid:]))


def _merge(left, right):
    """정렬된 두 리스트를 하나로 합친다. 동률이면 left를 먼저 취해 안정성을 지킨다."""
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        if right[j][0] < left[i][0]:
            merged.append(right[j])
            j += 1
        else:
            merged.append(left[i])
            i += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged
