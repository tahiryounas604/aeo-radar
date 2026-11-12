import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from aeo_radar.models import Brand, Competitor


@pytest.fixture
def brand():
    return Brand(
        name="Acme",
        aliases=["Acme Cloud"],
        competitors=[
            Competitor(name="RivalTool", aliases=[]),
            Competitor(name="OtherApp", aliases=[]),
        ],
        prompts=["best project tool", "cheapest project tool"],
    )
