"""Tests for rendering statistics retrieved from the backend."""

from types import SimpleNamespace

import pytest
import streamlit as st

from frontend.views import stats_view


class FakeSessionState(dict):
    """Dict-like state for the Streamlit statistics view."""


def test_stats_view_queries_active_player_and_leaderboard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(st, "session_state", FakeSessionState(player_id=42))
    requested_urls: list[str] = []
    rendered_tables: list[list[dict[str, object]]] = []
    rendered_headings: list[str] = []
    rendered_markup: list[str] = []

    def mock_get(url: str, **_kwargs: object) -> SimpleNamespace:
        assert _kwargs["timeout"] == 5
        requested_urls.append(url)
        if url.endswith("/42/stats"):
            payload = {
                "user_id": 42,
                "username": "Player",
                "games_played": 4,
                "games_won": 3,
                "current_streak": 2,
                "max_streak": 3,
                "win_rate": 75.0,
            }
        else:
            payload = [
                {
                    "rank": 1,
                    "user_id": 42,
                    "username": "Player",
                    "games_played": 4,
                    "games_won": 3,
                    "current_streak": 2,
                    "max_streak": 3,
                    "win_rate": 75.0,
                }
            ]
        return SimpleNamespace(status_code=200, json=lambda: payload)

    def capture_markdown(content: str, **kwargs: object) -> None:
        assert kwargs["unsafe_allow_html"] is True
        rendered_markup.append(content)

    def capture_dataframe(data: list[dict[str, object]], **kwargs: object) -> None:
        assert kwargs["use_container_width"] is True
        assert kwargs["hide_index"] is True
        rendered_tables.append(data)

    monkeypatch.setattr(stats_view.requests, "get", mock_get)
    monkeypatch.setattr(st, "subheader", rendered_headings.append)
    monkeypatch.setattr(st, "markdown", capture_markdown)
    monkeypatch.setattr(st, "divider", lambda: None)
    monkeypatch.setattr(st, "dataframe", capture_dataframe)

    stats_view.render()

    assert requested_urls == [
        f"{stats_view.BACKEND_URL}/api/v1/users/42/stats",
        f"{stats_view.BACKEND_URL}/api/v1/leaderboard",
    ]
    assert rendered_headings == ["📊 Player's Statistics", "🌍 Global Leaderboard"]
    assert "75%" in rendered_markup[0]
    assert rendered_tables == [
        [
            {
                "Rank": 1,
                "Player": "Player",
                "Played": 4,
                "Wins": 3,
                "Win %": "75%",
                "Longest Streak": 3,
            }
        ]
    ]
