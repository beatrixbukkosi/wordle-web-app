"""FastAPI controller routing HTTP requests for the Wordle application."""

from contextlib import asynccontextmanager
import logging
import sys
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from models.game_schemas import (
    GameStartResponse,
    GameStateResponse,
    GuessRequest,
    GuessResponse,
    GuessResult,
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
def start_game() -> GameStartResponse:
    """Initializes a new game session and returns the initial state without revealing the secret word."""
    try:
        game = game_service.create_game()
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
            result = game_service.submit_guess(request.session_id, guess_upper)
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
