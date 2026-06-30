import pytest


@pytest.fixture(autouse=True)
def isolate_team_profile_store(monkeypatch, tmp_path):
    monkeypatch.setenv("TEAM_PROFILE_STORE_PATH", str(tmp_path / "team_profiles.json"))
