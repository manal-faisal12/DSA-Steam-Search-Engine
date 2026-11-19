
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.indexer.index_builder import build_index


@pytest.fixture(scope="session")
def base_index_dir():
    """Build one temporary index for the complete test session."""
    project_root = Path(__file__).resolve().parents[1]
    dataset = project_root / "data" / "test" / "games_test.jsonl"

    with tempfile.TemporaryDirectory() as temporary_directory:
        index_dir = Path(temporary_directory) / "index"

        build_index(
            data_path=dataset,
            index_dir=index_dir
        )

        yield index_dir


@pytest.fixture
def temporary_index(tmp_path, base_index_dir):
    """Give each dynamic test its own independent index copy."""
    test_index = tmp_path / "index"
    shutil.copytree(base_index_dir, test_index)
    return test_index
