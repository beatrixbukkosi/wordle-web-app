# Test suite for additional behavior not specific to AC1-AC8


from types import SimpleNamespace
import pytest
from frontend.views import game_view

from types import SimpleNamespace
from typing import Any
import pytest
import streamlit as st
import state_manager
from views import profile_view

import logging
from typing import Generator
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import main as game_api
from models.game_schemas import GuessRequest
from repositories.database import Base
from repositories.game_repository import GameRepository
from services.game_service import GameService

from typing import Generator
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import main as game_api
from models.game_schemas import (
    GamePlayerAssociationRequest,
    GuessRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from repositories.database import Base, init_db
from repositories.game_repository import GameRepository
from repositories.user_repository import UserRepository
from services.game_service import GameService

from types import SimpleNamespace
import pytest
import streamlit as st
from frontend.views import stats_view


class FakeSessionState(dict):
    """Dict-like mock of Streamlit session_state supporting attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


@pytest.fixture
def player_service() -> Generator[GameService, None, None]:
    """Configures the API with an isolated in-memory database."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=test_engine,
    )
    repository = GameRepository(session_factory=test_session_factory)
    user_repository = UserRepository(session_factory=test_session_factory)
    service = GameService(repository=repository, user_repository=user_repository)
    service.load_dictionaries()

    original_service = game_api.game_service
    game_api.game_service = service
    yield service
    game_api.game_service = original_service
    test_engine.dispose()


def _create_user(username: str) -> int:
    return game_api.create_user(UserCreateRequest(username=username)).id


def _complete_win(session_id: str, secret_word: str) -> None:
    game_api.validate_guess(
        GuessRequest(session_id=session_id, guess=secret_word)
    )


def _complete_loss(service: GameService, session_id: str, secret_word: str) -> None:
    wrong_guess = next(
        word for word in service.valid_guesses if word != secret_word
    )
    for _ in range(6):
        game_api.validate_guess(
            GuessRequest(session_id=session_id, guess=wrong_guess)
        )


def test_profiles_are_persistent_and_stats_update_once_on_completion(
    player_service: GameService,
) -> None:
    """Verifies profile reuse and aggregate statistics after wins and losses."""
    user_id = _create_user("PlayerOne")
    assert _create_user("PlayerOne") == user_id

    won_game = game_api.start_game(user_id=user_id)
    won_session = player_service.get_game_state(won_game.session_id)
    assert won_session is not None
    _complete_win(won_game.session_id, won_session.secret_word)

    lost_game = game_api.start_game(user_id=user_id)
    lost_session = player_service.get_game_state(lost_game.session_id)
    assert lost_session is not None
    _complete_loss(player_service, lost_game.session_id, lost_session.secret_word)

    stats = game_api.get_user_stats(user_id)
    assert stats.games_played == 2
    assert stats.games_won == 1
    assert stats.current_streak == 0
    assert stats.max_streak == 1
    assert stats.win_rate == 50

    with pytest.raises(ValueError, match="already finished"):
        player_service.submit_guess(lost_game.session_id, "CRANE")
    assert game_api.get_user_stats(user_id).games_played == 2


def test_keyboard_colors_keep_the_strongest_feedback() -> None:
    """Verifies requirement 9 behavior."""
    board = [
        list("ABCDE"),
        list("AFCDE"),
        list("CDEFG"),
    ]
    row_colors = [
        ["YELLOW", "GREEN", "GRAY", "GRAY", "YELLOW"],
        ["GREEN", "GRAY", "YELLOW", "GREEN", "GRAY"],
        ["GREEN", "GRAY", "GRAY", "GRAY", "GRAY"],
    ]

    assert game_view.get_keyboard_colors(board, row_colors) == {
        "A": "GREEN",
        "B": "GREEN",
        "C": "GREEN",
        "D": "GREEN",
        "E": "YELLOW",
        "F": "GRAY",
        "G": "GRAY",
    }


def test_keyboard_styles_target_each_colored_key() -> None:
    """Verifies requirement 9 behavior."""
    styles = game_view.get_keyboard_styles({"A": "GREEN", "Q": "YELLOW"})

    assert ".st-key-btn_A button" in styles
    assert "background-color: #6aaa64 !important" in styles
    assert ".st-key-btn_Q button" in styles
    assert "background-color: #c9b458 !important" in styles
    assert "height: 48px !important" in styles
    assert "transform: none !important" in styles
    assert "transition: none !important" in styles
    assert "[data-testid='stHorizontalBlock']:has(" in styles
    assert ":nth-child(9))" in styles


def test_submit_button_style_shows_valid_and_invalid_guesses() -> None:
    """Verifies submit-button styling for valid and invalid guesses."""
    valid_style = game_view.get_submit_button_style(True)
    invalid_style = game_view.get_submit_button_style(False)

    assert "background-color: #6aaa64" in valid_style
    assert "background-color: #d9534f" in invalid_style
    assert "button[kind='primary']" in valid_style
    assert "button[kind='primary']:disabled" in invalid_style
    assert "cursor: not-allowed !important" in invalid_style
    assert "height: 48px !important" in valid_style
    assert "transform: none !important" in valid_style
    assert "transition: none !important" in valid_style
    assert game_view.get_submit_button_style(None) == ""


def test_start_new_game_sets_session_id_in_url_and_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that starting a new game updates session_state and URL query parameters."""
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {}

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(
        state_manager.requests,
        "post",
        lambda url, **kwargs: SimpleNamespace(
            status_code=201,
            json=lambda: {
                "session_id": "new-session-789",
                "word_length": 5,
                "max_attempts": 6,
                "remaining_attempts": 6,
                "game_status": "IN_PROGRESS",
                "guesses": [],
            },
        ),
    )

    state_manager.start_new_game()

    assert fake_state.session_id == "new-session-789"
    assert fake_query_params["session_id"] == "new-session-789"
    assert fake_state.current_row == 0
    assert fake_state.current_col == 0
    assert fake_state.board == [["" for _ in range(5)] for _ in range(6)]
    assert fake_state.row_colors == [[None for _ in range(5)] for _ in range(6)]
    assert "secret_word" not in fake_state
    assert "target_word" not in fake_state


def test_start_new_game_associates_active_player(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies requirement 9 behavior."""
    fake_state = FakeSessionState(player_id=42)
    fake_query_params: dict[str, str] = {}
    request_params: list[dict[str, int] | None] = []

    def mock_post(url: str, **kwargs: Any) -> SimpleNamespace:
        request_params.append(kwargs.get("params"))
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"session_id": "player-game-session"},
        )

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "post", mock_post)

    state_manager.start_new_game()

    assert request_params == [{"user_id": 42}]


def test_initialize_without_profile_does_not_create_guest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies requirement 9 behavior."""
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {}
    requested_urls: list[str] = []
    requested_profile_urls: list[str] = []

    def mock_get(url: str, **kwargs: Any) -> SimpleNamespace:
        requested_profile_urls.append(url)
        return SimpleNamespace(
            status_code=200,
            json=lambda: [{"id": 7, "username": "ExistingPlayer"}],
        )

    def mock_post(url: str, **kwargs: Any) -> SimpleNamespace:
        requested_urls.append(url)
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"session_id": "anonymous-session"},
        )

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "get", mock_get)
    monkeypatch.setattr(state_manager.requests, "post", mock_post)

    state_manager.initialize_state()

    assert fake_state.player_name == ""
    assert fake_state.saved_profiles == ["ExistingPlayer"]
    assert fake_state.profiles_loaded is True
    assert "player_id" not in fake_state
    assert requested_profile_urls == [f"{state_manager.BACKEND_URL}/api/v1/users"]
    assert requested_urls == [f"{state_manager.BACKEND_URL}/api/v1/game/start"]
    assert "player" not in fake_query_params


def test_existing_profiles_are_selectable_without_an_active_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies saved profiles and the create-profile action are visible."""
    fake_state = FakeSessionState(
        player_name="",
        saved_profiles=["ExistingPlayer"],
        profile_mode="view",
    )
    selectbox_options: list[str] = []
    button_labels: list[str] = []

    class FakeColumn:
        def button(self, label: str, **kwargs: Any) -> None:
            button_labels.append(label)

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(state_manager, "load_saved_profiles", lambda: None)
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        st,
        "selectbox",
        lambda label, options, **kwargs: selectbox_options.extend(options),
    )
    monkeypatch.setattr(st, "columns", lambda count: [FakeColumn() for _ in range(count)])

    profile_view.render()

    assert selectbox_options == ["ExistingPlayer"]
    assert "✅ Select" in button_labels
    assert "➕ Create new profile" in button_labels


def test_rename_active_profile_uses_update_and_keeps_profile_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies requirement 9 behavior."""
    fake_state = FakeSessionState(
        player_id=42,
        player_name="OldName",
        profile_original_name="OldName",
        saved_profiles=["OldName", "Other"],
        profile_mode="edit",
        name_input="NewName",
    )
    fake_query_params: dict[str, str] = {}
    request_data: dict[str, Any] = {}

    def mock_put(url: str, **kwargs: Any) -> SimpleNamespace:
        request_data.update({"url": url, **kwargs})
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"id": 42, "username": "NewName"},
        )

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "put", mock_put)
    monkeypatch.setattr(
        state_manager.requests,
        "post",
        lambda *args, **kwargs: pytest.fail("Renaming must not create a profile"),
    )

    profile_view.save_profile()

    assert request_data["url"].endswith("/api/v1/users/42")
    assert request_data["json"] == {"username": "NewName"}
    assert fake_state.player_id == 42
    assert fake_state.player_name == "NewName"
    assert fake_state.saved_profiles == ["Other", "NewName"]
    assert fake_query_params["player"] == "NewName"
    assert fake_state.profile_mode == "view"


def test_switching_profile_starts_a_new_game(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies requirement 9 behavior."""
    fake_state = FakeSessionState(
        player_id=12,
        profile_selectbox="AnotherPlayer",
        profile_mode="switch",
    )
    selected_profiles: list[str] = []
    started_games: list[bool] = []

    def select_profile(username: str) -> None:
        selected_profiles.append(username)
        fake_state.player_id = 24

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(state_manager, "select_profile", select_profile)
    monkeypatch.setattr(
        state_manager,
        "start_new_game",
        lambda: started_games.append(True),
    )

    profile_view.apply_switch_profile()

    assert selected_profiles == ["AnotherPlayer"]
    assert started_games == [True]
    assert fake_state.profile_mode == "view"


def test_delete_last_profile_leaves_no_guest_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies requirement 9 behavior."""
    fake_state = FakeSessionState(
        player_id=42,
        player_name="RemoveMe",
        saved_profiles=["RemoveMe"],
    )
    fake_query_params: dict[str, str] = {}
    deleted_urls: list[str] = []
    post_urls: list[str] = []

    def mock_delete(url: str, **kwargs: Any) -> SimpleNamespace:
        deleted_urls.append(url)
        return SimpleNamespace(status_code=204)

    def mock_post(url: str, **kwargs: Any) -> SimpleNamespace:
        post_urls.append(url)
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"session_id": "anonymous-game"},
        )

    monkeypatch.setattr(
        state_manager.requests,
        "get",
        lambda *args, **kwargs: SimpleNamespace(status_code=200, json=lambda: []),
    )
    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "delete", mock_delete)
    monkeypatch.setattr(state_manager.requests, "post", mock_post)

    assert state_manager.delete_active_profile() is True

    assert deleted_urls == [f"{state_manager.BACKEND_URL}/api/v1/users/42"]
    assert post_urls == [f"{state_manager.BACKEND_URL}/api/v1/game/start"]
    assert fake_state.player_name == ""
    assert "player_id" not in fake_state
    assert "RemoveMe" not in fake_state.saved_profiles
    assert "player" not in fake_query_params
    assert fake_state.session_id == "anonymous-game"


def test_invalid_url_session_id_triggers_new_game(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that when URL contains an invalid or expired session_id, a fresh game is created."""
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {"session_id": "expired-session-id"}

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager, "load_saved_profiles", lambda: None)
    monkeypatch.setattr(state_manager, "fetch_game_state", lambda session_id: None)
    monkeypatch.setattr(
        state_manager.requests,
        "post",
        lambda url, **kwargs: SimpleNamespace(
            status_code=201,
            json=lambda: {
                "session_id": "fallback-fresh-session",
                "word_length": 5,
                "max_attempts": 6,
                "remaining_attempts": 6,
                "game_status": "IN_PROGRESS",
                "guesses": [],
            },
        ),
    )

    state_manager.initialize_state()

    assert fake_state.session_id == "fallback-fresh-session"
    assert fake_query_params["session_id"] == "fallback-fresh-session"
    assert fake_state.current_row == 0


def test_start_game_generates_session_id_and_hides_secret_word(test_setup: GameService) -> None:
    """Verifies that starting a game generates a unique session_id and never exposes secret_word."""
    response = game_api.start_game()
    data = response.model_dump()

    assert "session_id" in data
    assert isinstance(data["session_id"], str)
    assert len(data["session_id"]) > 0

    assert data["word_length"] == 5
    assert data["max_attempts"] == 6
    assert data["remaining_attempts"] == 6
    assert data["game_status"] == "IN_PROGRESS"
    assert data["guesses"] == []

    # Security check: secret_word and target_word must NEVER be in client response
    assert "secret_word" not in data
    assert "target_word" not in data
    assert not hasattr(response, "secret_word")
    assert not hasattr(response, "target_word")


def test_start_game_logs_secret_word_and_session_id(
    test_setup: GameService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verifies that backend logs the secret word and session_id upon game creation for dev testing."""
    with caplog.at_level(logging.INFO):
        response = game_api.start_game()
        session_id = response.session_id

        matching_logs = [
            record.message
            for record in caplog.records
            if session_id in record.message and "Secret Word:" in record.message
        ]
        assert len(matching_logs) == 1
        assert "New game started" in matching_logs[0]


def test_query_nonexistent_session_raises_404(test_setup: GameService) -> None:
    """Verifies that querying an unknown session_id raises HTTPException 404."""
    with pytest.raises(HTTPException) as exc_info:
        game_api.get_game_state("non-existent-session-id")
    assert exc_info.value.status_code == 404


def test_associating_an_unowned_completed_game_records_its_result_once(
    player_service: GameService,
) -> None:
    """Verifies requirement 9 behavior."""
    user_id = _create_user("Winner")
    game = game_api.start_game()
    session = player_service.get_game_state(game.session_id)
    assert session is not None
    _complete_win(game.session_id, session.secret_word)

    assert game_api.get_user_stats(user_id).games_played == 0
    game_api.associate_game_with_player(
        game.session_id,
        GamePlayerAssociationRequest(user_id=user_id),
    )
    game_api.associate_game_with_player(
        game.session_id,
        GamePlayerAssociationRequest(user_id=user_id),
    )

    stats = game_api.get_user_stats(user_id)
    assert stats.games_played == 1
    assert stats.games_won == 1
    assert stats.current_streak == 1


def test_leaderboard_ranks_by_wins_then_win_rate(
    player_service: GameService,
) -> None:
    """Verifies requirement 9 behavior."""
    higher_win_rate_id = _create_user("HigherRate")
    lower_win_rate_id = _create_user("LowerRate")

    for user_id in (higher_win_rate_id, lower_win_rate_id):
        game = game_api.start_game(user_id=user_id)
        session = player_service.get_game_state(game.session_id)
        assert session is not None
        _complete_win(game.session_id, session.secret_word)

    lower_rate_loss = game_api.start_game(user_id=lower_win_rate_id)
    lost_session = player_service.get_game_state(lower_rate_loss.session_id)
    assert lost_session is not None
    _complete_loss(
        player_service,
        lower_rate_loss.session_id,
        lost_session.secret_word,
    )

    leaderboard = game_api.get_leaderboard(limit=10)
    assert leaderboard[0].user_id == higher_win_rate_id
    assert leaderboard[0].win_rate == 100
    assert leaderboard[1].user_id == lower_win_rate_id
    assert leaderboard[1].win_rate == 50


def test_database_startup_adds_player_link_to_existing_game_table() -> None:
    """Verifies requirement 9 behavior."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE game_sessions (session_id VARCHAR(36) PRIMARY KEY)"
        )

    init_db(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("game_sessions")}
    assert "player_id" in columns
    engine.dispose()


def test_renaming_profile_preserves_id_and_statistics(
    player_service: GameService,
) -> None:
    """Verifies requirement 9 behavior."""
    user_id = _create_user("OriginalName")
    game = game_api.start_game(user_id=user_id)
    session = player_service.get_game_state(game.session_id)
    assert session is not None
    _complete_win(game.session_id, session.secret_word)

    renamed = game_api.update_user(
        user_id,
        UserUpdateRequest(username="UpdatedName"),
    )
    stats = game_api.get_user_stats(user_id)

    assert renamed.id == user_id
    assert renamed.username == "UpdatedName"
    assert stats.username == "UpdatedName"
    assert stats.games_played == 1
    assert stats.games_won == 1


def test_renaming_to_existing_name_returns_conflict(
    player_service: GameService,
) -> None:
    """Verifies requirement 9 behavior."""
    first_user_id = _create_user("First")
    second_user_id = _create_user("Second")

    with pytest.raises(HTTPException) as exc_info:
        game_api.update_user(
            second_user_id,
            UserUpdateRequest(username="First"),
        )

    assert exc_info.value.status_code == 409
    assert game_api.get_user_stats(second_user_id).username == "Second"
    assert game_api.get_user_stats(first_user_id).username == "First"


def test_deleting_profile_removes_stats_and_unlinks_existing_games(
    player_service: GameService,
) -> None:
    """Verifies requirement 9 behavior."""
    user_id = _create_user("ToDelete")
    game = game_api.start_game(user_id=user_id)

    assert game_api.delete_user(user_id) is None
    assert player_service.user_repository.get_by_id(user_id) is None
    assert player_service.user_repository.get_leaderboard(limit=10) == []
    session = player_service.get_game_state(game.session_id)
    assert session is not None
    assert session.player_id is None

    with pytest.raises(HTTPException) as exc_info:
        game_api.delete_user(user_id)
    assert exc_info.value.status_code == 404


def test_stats_view_queries_active_player_and_leaderboard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies requirement 9 behavior."""
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
