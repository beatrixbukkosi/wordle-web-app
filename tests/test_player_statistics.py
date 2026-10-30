"""Tests for persistent player profiles, game statistics, and the leaderboard."""

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


def test_associating_an_unowned_completed_game_records_its_result_once(
    player_service: GameService,
) -> None:
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
