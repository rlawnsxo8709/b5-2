"""미션 제약(표준 정렬 API·그래프 라이브러리·외부 라이브러리 금지)을 AST로 검사한다."""

import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANNED_MODULES = {"heapq", "bisect", "networkx", "graphlib"}
OWN_PACKAGES = {"mini_git", "tests"}


def source_files():
    """검사 대상: mini_git/*.py, main.py, tests/*.py"""
    files = list((ROOT / "mini_git").glob("*.py")) + list((ROOT / "tests").glob("*.py"))
    files.append(ROOT / "main.py")
    return files


def violations(source):
    """소스 문자열에서 금지 사항을 찾아 설명 문자열 리스트로 돌려준다."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id == "sorted":
            found.append(f"line {node.lineno}: sorted 사용")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
            found.append(f"line {node.lineno}: .sort() 호출")
        elif isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
            found.extend(_import_problems(node.lineno, modules))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            found.extend(_import_problems(node.lineno, [node.module]))
    return found


def _import_problems(lineno, modules):
    problems = []
    for module in modules:
        top = module.split(".")[0]
        if top in BANNED_MODULES:
            problems.append(f"line {lineno}: 금지 모듈 import {module}")
        elif top not in sys.stdlib_module_names and top not in OWN_PACKAGES:
            problems.append(f"line {lineno}: 외부 라이브러리 import {module}")
    return problems


class TestConstraints(unittest.TestCase):
    def test_scans_the_expected_files(self):
        names = {p.name for p in source_files()}
        for expected in ("main.py", "cli.py", "graph.py", "sorting.py", "test_constraints.py"):
            self.assertIn(expected, names)

    def test_no_forbidden_usage_in_project(self):
        for path in source_files():
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertEqual(violations(path.read_text(encoding="utf-8")), [])

    def test_detector_catches_violations(self):
        # 검사기가 항상 통과하는 빈 껍데기가 아님을 보장한다.
        self.assertEqual(len(violations("x = sorted(items)")), 1)
        self.assertEqual(len(violations("items.sort()")), 1)
        self.assertEqual(len(violations("import heapq")), 1)
        self.assertEqual(len(violations("from bisect import insort")), 1)
        self.assertEqual(len(violations("import networkx as nx")), 1)
        self.assertEqual(len(violations("from graphlib import TopologicalSorter")), 1)
        self.assertEqual(len(violations("import numpy")), 1)
        self.assertEqual(violations("import re\nfrom collections import deque\nx = [1].copy()"), [])


if __name__ == "__main__":
    unittest.main()
