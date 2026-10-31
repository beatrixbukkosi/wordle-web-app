# Test suite for AC2: Normal Operation (Victory)


from types import SimpleNamespace
import pytest
from frontend.views import game_view

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

from models.game_schemas import UserCreateRequest
from repositories.user_repository import UserRepository


def _create_user(username: str) -> int:
    return game_api.create_user(UserCreateRequest(username=username)).id


def _complete_win(session_id: str, secret_word: str) -> None:
    game_api.validate_guess(
        GuessRequest(session_id=session_id, guess=secret_word)
    )


class FakeSessionState:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


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


def test_winning_guess_sends_active_player_id_and_refreshes_streak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies requirement 2 behavior."""
    state = FakeSessionState(
        game_won=False,
        current_row=0,
        current_col=5,
        guess_is_valid=True,
        board=[list("APPLE") for _ in range(6)],
        row_colors=[[None] * 5 for _ in range(6)],
        session_id="session-1",
        player_id=21,
    )
    submitted_payload: dict[str, object] = {}

    def mock_post(url: str, **kwargs: object) -> SimpleNamespace:
        assert url.endswith("/api/v1/game/validate")
        submitted_payload.update(kwargs["json"])
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "is_valid": True,
                "is_winning": True,
                "game_status": "WON",
                "colors": ["GREEN"] * 5,
            },
        )

    monkeypatch.setattr(game_view.st, "session_state", state)
    monkeypatch.setattr(game_view.requests, "post", mock_post)
    monkeypatch.setattr(
        game_view.state_manager,
        "load_player_stats",
        lambda: setattr(state, "current_streak", 1),
    )

    game_view.submit_guess()

    assert submitted_payload["session_id"] == "session-1"
    assert submitted_payload["user_id"] == 21
    assert state.game_won is True
    assert state.current_streak == 1


def test_winning_guess_updates_game_status_to_won(test_setup: GameService) -> None:
    """Verifies AC2: a correct guess ends the game with all letters green."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    # Retrieve internal secret word from repository for test verification
    session_model = game_api.game_service.repository.get_by_session_id(session_id)
    assert session_model is not None
    secret = session_model.secret_word

    win_resp = game_api.validate_guess(
        GuessRequest(session_id=session_id, guess=secret)
    )
    win_data = win_resp.model_dump()
    assert win_data["is_winning"] is True
    assert win_data["game_status"] == "WON"
    assert win_data["colors"] == ["GREEN"] * 5

def test_winning_game_increments_player_wins_and_streak(player_service: GameService) -> None:
    """Verifies AC2: completing a win increments wins and the current streak."""
    user_id = _create_user("Winner")
    game = game_api.start_game(user_id=user_id)
    session = player_service.get_game_state(game.session_id)
    assert session is not None
    _complete_win(game.session_id, session.secret_word)
    stats = game_api.get_user_stats(user_id)
    assert stats.games_played == 1
    assert stats.games_won == 1
    assert stats.current_streak == 1
