from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_live_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("HOME_CONTROL_ANTHROPIC_KEY", raising=False)
