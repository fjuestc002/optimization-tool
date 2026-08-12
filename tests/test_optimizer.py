from pathlib import Path

from optimization_tool.main import run_optimization


def test_run_optimization_imports(monkeypatch):
    class DummyRunner:
        def __init__(self, run_directory, csv_filename):
            self.run_directory = run_directory

        def get_current_test_name(self):
            return '""MyLib:MyCell"'

        def download_output_csv(self):
            return Path("outputs_MyLib_MyCell_maestro.csv")

        def load_specs(self):
            return ["name"], __import__("numpy").array([1.0]), ["spec"]

    import optimization_tool.main as main_module

    monkeypatch.setattr(main_module, "OptimizationRunner", DummyRunner)

    result = run_optimization(Path("."), iterations=1)
    assert result["spec_count"] == 1
