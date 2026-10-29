import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MAPPING_EPI_DONNEES", tempfile.mkdtemp(prefix="mapping_epi_tests_"))

from core.storage import load_json  # noqa: E402


@pytest.fixture
def demo():
    return load_json(ROOT / "sample_data" / "cas_exemple_fictif.json")
