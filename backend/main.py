"""FastAPI controller routing HTTP requests for the Wordle application."""

from contextlib import asynccontextmanager
import logging
import sys
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from models.game_schemas import (
    GameStartResponse,
    GamePlayerAssociationRequest,
    GameStateResponse,
    GuessRequest,
    GuessResponse,
    GuessResult,
    LeaderboardEntry,
    UserCreateRequest,
    UserResponse,
    UserStatsResponse,
    UserUpdateRequest,
    WordValidationRequest,
    WordValidationResponse,
)
from repositories.database import init_db
from services.game_service import GameService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("wordle_api")

game_service = GameService()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle."""
    init_db()
    game_service.load_dictionaries()
    yield


app = FastAPI(title="Wordle API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post(
    "/api/v1/game/start",
    response_model=GameStartResponse,
    status_code=status.HTTP_201_CREATED,
)
@app.get("/api/v1/game/start", response_model=GameStartResponse)
def start_game(user_id: int | None = None) -> GameStartResponse:
    """Initializes a new game session and returns the initial state without revealing the secret word."""
    if user_id is not None and game_service.user_repository.get_by_id(user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found",
        )

    try:
        game = game_service.create_game(player_id=user_id)
        return GameStartResponse(
            session_id=game.session_id,
            word_length=game.word_length,
            max_attempts=game.max_attempts,
            remaining_attempts=game.remaining_attempts,
            game_status=game.game_status,
            guesses=[],
        )
    except ValueError as error:
        logger.error("Failed to start new game: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@app.post("/api/v1/users", response_model=UserResponse)
def create_user(request: UserCreateRequest) -> UserResponse:
    """Creates or returns a persistent player profile."""
    try:
        user = game_service.user_repository.create_or_get_user(request.username)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    return UserResponse(id=user.id, username=user.username)


@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, request: UserUpdateRequest) -> UserResponse:
    """Renames an existing profile while preserving its statistics."""
    try:
        user = game_service.user_repository.update_username(user_id, request.username)
    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
                if "already in use" in str(error)
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=str(error),
        ) from error
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found",
        )
    return UserResponse(id=user.id, username=user.username)


@app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int) -> None:
    """Deletes a player profile and statistics while retaining unowned games."""
    if not game_service.user_repository.delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found",
        )


@app.get("/api/v1/users", response_model=list[UserResponse])
def list_users() -> list[UserResponse]:
    """Lists persistent profiles for the frontend profile selector."""
    return [
        UserResponse(id=user.id, username=user.username)
        for user in game_service.user_repository.list_users()
    ]


@app.get("/api/v1/users/{user_id}/stats", response_model=UserStatsResponse)
def get_user_stats(user_id: int) -> UserStatsResponse:
    """Returns the requested player's stored statistics."""
    result = game_service.user_repository.get_stats(user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found",
        )

    user, stats = result
    return UserStatsResponse(
        user_id=user.id,
        username=user.username,
        games_played=stats.games_played,
        games_won=stats.games_won,
        current_streak=stats.current_streak,
        max_streak=stats.max_streak,
        win_rate=stats.win_rate,
    )


@app.get("/api/v1/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
) -> list[LeaderboardEntry]:
    """Returns players ranked by total wins and then win rate."""
    entries = game_service.user_repository.get_leaderboard(limit)
    return [
        LeaderboardEntry(
            rank=rank,
            user_id=user.id,
            username=user.username,
            games_played=stats.games_played,
            games_won=stats.games_won,
            current_streak=stats.current_streak,
            max_streak=stats.max_streak,
            win_rate=stats.win_rate,
        )
        for rank, (user, stats) in enumerate(entries, start=1)
    ]


@app.post("/api/v1/game/{session_id}/associate")
def associate_game_with_player(
    session_id: str,
    request: GamePlayerAssociationRequest,
) -> dict[str, str]:
    """Associates an unowned game with a player and accounts for completed games."""
    try:
        game_service.associate_game_with_player(session_id, request.user_id)
    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
                if "belongs to another player" in str(error)
                else status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error
    return {"status": "associated"}


@app.get("/api/v1/game/{session_id}", response_model=GameStateResponse)
@app.get("/api/v1/game/state/{session_id}", response_model=GameStateResponse)
def get_game_state(session_id: str) -> GameStateResponse:
    """Queries the stored game state for the given session identifier."""
    game = game_service.get_game_state(session_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found",
        )
    return GameStateResponse(
        session_id=game.session_id,
        word_length=game.word_length,
        max_attempts=game.max_attempts,
        remaining_attempts=game.remaining_attempts,
        game_status=game.game_status,
        guesses=[GuessResult(**guess) for guess in game.guesses],
    )


@app.post(
    "/api/v1/game/word-validation",
    response_model=WordValidationResponse,
)
def validate_word(request: WordValidationRequest) -> WordValidationResponse:
    """Checks a word against the accepted-guess dictionary without changing game state."""
    guess = request.guess.strip().upper()
    return WordValidationResponse(
        is_valid=len(guess) == 5 and game_service.is_valid_guess(guess)
    )


@app.post("/api/v1/game/validate", response_model=GuessResponse)
@app.post("/api/v1/game/guess", response_model=GuessResponse)
def validate_guess(request: GuessRequest) -> GuessResponse:
    """Validates and evaluates a submitted guess against server session state."""
    guess_upper = request.guess.strip().upper()

    if request.session_id:
        game = game_service.get_game_state(request.session_id)
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game session not found",
            )
        if game.game_status != "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game is already finished",
            )

        try:
            result = game_service.submit_guess(
                request.session_id,
                guess_upper,
                player_id=request.user_id,
            )
            return GuessResponse(**result)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

    # Stateless fallback for testing / direct evaluation without session persistence
    if request.target_word:
        is_valid = game_service.is_valid_guess(guess_upper)
        is_winning = bool(is_valid and guess_upper == request.target_word.upper())
        colors = (
            game_service.evaluate_guess(guess_upper, request.target_word)
            if is_valid
            else None
        )
        return GuessResponse(
            guess=guess_upper,
            is_valid=is_valid,
            is_winning=is_winning,
            colors=colors,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either session_id or target_word must be provided",
    )
