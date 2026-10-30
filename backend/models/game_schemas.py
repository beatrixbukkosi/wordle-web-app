"""Pydantic schemas for Wordle API requests and responses."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GuessResult(BaseModel):
    """Schema representing an evaluated guess and its letter colors."""

    guess: str
    colors: list[str]


class GameStartResponse(BaseModel):
    """Response returned when a new game session starts."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    word_length: int = 5
    max_attempts: int = 6
    remaining_attempts: int = 6
    game_status: str = "IN_PROGRESS"
    guesses: list[GuessResult] = Field(default_factory=list)


class GameStateResponse(BaseModel):
    """Response returned when querying the current game state."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    word_length: int = 5
    max_attempts: int = 6
    remaining_attempts: int
    game_status: str
    guesses: list[GuessResult] = Field(default_factory=list)


class GuessRequest(BaseModel):
    """Request payload for submitting or validating a guess."""

    guess: str
    session_id: str | None = None
    target_word: str | None = None


class WordValidationRequest(BaseModel):
    """Request payload for checking whether a word is an accepted guess."""

    guess: str


class WordValidationResponse(BaseModel):
    """Response indicating whether a word is an accepted guess."""

    is_valid: bool


class GuessResponse(BaseModel):
    """Response returned after submitting or validating a guess."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str | None = None
    guess: str
    is_valid: bool
    is_winning: bool = False
    colors: list[str] | None = None
    remaining_attempts: int | None = None
    game_status: str | None = None

    def __getitem__(self, item: str) -> Any:
        """Enables dictionary-like subscripting for backward compatibility with unit tests."""
        return getattr(self, item)
