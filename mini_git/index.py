"""역색인: 커밋 메시지 키워드와 작성자로 후보 커밋을 바로 찾는다."""


def tokenize(text):
    """공백 기준으로 나누고 소문자로 바꾼 토큰을 중복 없이, 처음 나온 순서대로 돌려준다."""
    seen = set()
    tokens = []
    for word in text.split():
        token = word.lower()
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


class InvertedIndex:
    """keyword -> [commit_hash], author -> [commit_hash] 두 개의 역색인.

    커밋이 만들어지는 시점에 add_commit으로 갱신한다. 각 목록은 추가한 순서(= 생성 순서)를 유지하므로
    검색 결과도 자동으로 생성 순서다. 검색은 전체 커밋을 순회하지 않고 사전(dict) 조회로
    후보 목록을 곧바로 가져온다.
    """

    def __init__(self):
        self._by_keyword = {}
        self._by_author = {}

    def add_commit(self, commit_hash, message, author):
        """커밋 한 개를 색인에 넣는다. 토큰 수만큼의 사전 갱신 비용이 든다."""
        for token in tokenize(message):
            self._by_keyword.setdefault(token, []).append(commit_hash)
        self._by_author.setdefault(author, []).append(commit_hash)

    def search_keyword(self, query):
        """query의 모든 토큰이 메시지에 들어 있는 커밋(교집합)을 생성 순서로 돌려준다.

        가장 짧은 후보 목록을 기준으로 삼고 나머지 목록의 집합과 대조한다.
        비용은 O(후보 목록 크기의 합)이며, 색인되지 않은 커밋은 건드리지 않는다.
        """
        tokens = tokenize(query)
        if not tokens:
            return []
        postings = [self._by_keyword.get(token, []) for token in tokens]
        base = postings[0]
        for posting in postings[1:]:
            if len(posting) < len(base):
                base = posting
        others = [set(p) for p in postings if p is not base]
        return [h for h in base if all(h in other for other in others)]

    def search_author(self, name):
        """작성자 이름이 정확히(대소문자 구분) 같은 커밋을 생성 순서로 돌려준다."""
        return list(self._by_author.get(name, []))
