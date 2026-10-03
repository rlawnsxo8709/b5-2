"""Mini Git 공용 예외."""


class MiniGitError(Exception):
    """사용자에게 그대로 보여 줄 메시지를 담은 예외. str(e)가 곧 출력 문구다."""
