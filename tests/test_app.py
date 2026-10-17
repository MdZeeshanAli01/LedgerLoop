import ast
from pathlib import Path


def test_app_parses_and_delegates_calculations():
    source = Path(__file__).parents[1].joinpath("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "evaluate_all" in calls
    assert "write_result_json" in calls
    assert "write_result_csv" in calls
    assert "write_evidence_log" in calls
