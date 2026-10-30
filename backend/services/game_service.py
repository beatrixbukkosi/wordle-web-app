"""Business logic service for Wordle game management and guess evaluation."""

import logging
from pathlib import Path
import random
from typing import Any
import uuid

from repositories.game_repository import GameRepository, GameSessionModel
from repositories.user_repository import UserRepository

logger = logging.getLogger("wordle.game_service")

DEFAULT_WORD_LENGTH = 5
DEFAULT_MAX_ATTEMPTS = 6
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_WON = "WON"
STATUS_LOST = "LOST"


class GameService:
    """Encapsulates business rules, dictionary validation, and game progression."""

    def __init__(
        self,
        repository: GameRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.answers: list[str] = []
        self.valid_guesses: set[str] = set()
        self.repository: GameRepository = repository or GameRepository()
        self.user_repository = user_repository or UserRepository(
            session_factory=self.repository.session_factory
        )

    def load_dictionaries(self) -> None:
        """Loads target answers and valid guess word lists into memory."""
        project_root = Path(__file__).resolve().parents[2]
        data_dir = project_root / "data"

        answers_path = data_dir / "target-wordle-words.txt"
        guesses_path = data_dir / "valid-wordle-words.txt"

        try:
            with open(answers_path, "r", encoding="utf-8") as file:
                self.answers = [line.strip().upper() for line in file if line.strip()]

            with open(guesses_path, "r", encoding="utf-8") as file:
                self.valid_guesses = {line.strip().upper() for line in file if line.strip()}

            self.valid_guesses.update(self.answers)
            logger.info(
                "GameService initialized: %d answers, %d valid guesses.",
                len(self.answers),
                len(self.valid_guesses),
            )
        except FileNotFoundError as error:
            logger.error("Dictionary initialization failed: %s", error)

    def get_random_word(self) -> str:
        """Selects a random secret word from the answers list."""
        if not self.answers:
            raise ValueError("Dictionaries not loaded properly.")
        return random.choice(self.answers)

    def is_valid_guess(self, guess: str) -> bool:
        """Validates if the submitted guess exists in the accepted word dictionary."""
        return guess.upper() in self.valid_guesses

    def evaluate_guess(self, guess: str, target_word: str) -> list[str]:
        """Calculates GREEN, YELLOW, or GRAY match colors for each letter of the guess."""
        guess = guess.upper()
        target_word = target_word.upper()
        remaining_target_letters = list(target_word)
        colors = ["GRAY"] * len(guess)

        # First pass: find exact matches (GREEN)
        for index, letter in enumerate(guess):
            if index < len(target_word) and letter == target_word[index]:
                colors[index] = "GREEN"
                remaining_target_letters.remove(letter)

        # Second pass: find misplaced matches (YELLOW)
        for index, letter in enumerate(guess):
            if colors[index] == "GREEN":
                continue
            if letter in remaining_target_letters:
                colors[index] = "YELLOW"
                remaining_target_letters.remove(letter)

        return colors

    def create_game(
        self,
        word_length: int = DEFAULT_WORD_LENGTH,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        player_id: int | None = None,
    ) -> GameSessionModel:
        """Creates and persists a new game session, logging the secret word for development testing."""
        if player_id is not None and self.user_repository.get_by_id(player_id) is None:
            raise ValueError(f"Player {player_id} was not found.")

        session_id = str(uuid.uuid4())
        secret_word = self.get_random_word()

        game = self.repository.create_game(
            session_id=session_id,
            secret_word=secret_word,
            word_length=word_length,
            max_attempts=max_attempts,
            player_id=player_id,
        )

        logger.info(
            "New game started | Session ID: %s | Secret Word: %s",
            session_id,
            secret_word,
        )
        return game

    def get_game_state(self, session_id: str) -> GameSessionModel | None:
        """Retrieves stored game state for a given session identifier."""
        return self.repository.get_by_session_id(session_id)

    def associate_game_with_player(
        self, session_id: str, player_id: int
    ) -> GameSessionModel:
        """Associates an unowned game with a player and records prior completion."""
        game = self.repository.get_by_session_id(session_id)
        if game is None:
            raise ValueError("Game session not found.")
        if game.player_id is not None:
            if game.player_id != player_id:
                raise ValueError("Game session belongs to another player.")
            return game
        if self.user_repository.get_by_id(player_id) is None:
            raise ValueError(f"Player {player_id} was not found.")

        associated_game, was_associated = self.repository.associate_player(
            session_id,
            player_id,
        )
        if associated_game is None:
            raise ValueError("Game session not found.")
        if was_associated and associated_game.game_status in (STATUS_WON, STATUS_LOST):
            self.user_repository.record_game_result(
                player_id,
                won=associated_game.game_status == STATUS_WON,
            )
        return associated_game

    def submit_guess(
        self,
        session_id: str,
        guess: str,
        player_id: int | None = None,
    ) -> dict[str, Any]:
        """Evaluates a guess for an active game session, updates remaining attempts and status."""
        game = self.repository.get_by_session_id(session_id)
        if not game:
            raise ValueError("Game session not found.")

        if game.game_status != STATUS_IN_PROGRESS:
            raise ValueError("Game is already finished.")

        if game.player_id is None and player_id is not None:
            if self.user_repository.get_by_id(player_id) is None:
                raise ValueError(f"Player {player_id} was not found.")
            game.player_id = player_id

        guess_upper = guess.strip().upper()
        if not self.is_valid_guess(guess_upper):
            return {
                "session_id": session_id,
                "guess": guess_upper,
                "is_valid": False,
                "is_winning": False,
                "colors": None,
                "remaining_attempts": game.remaining_attempts,
                "game_status": game.game_status,
            }

        colors = self.evaluate_guess(guess_upper, game.secret_word)
        is_winning = guess_upper == game.secret_word.upper()
        remaining_attempts = max(0, game.remaining_attempts - 1)

        if is_winning:
            game_status = STATUS_WON
        elif remaining_attempts == 0:
            game_status = STATUS_LOST
        else:
            game_status = STATUS_IN_PROGRESS

        new_guesses = list(game.guesses) + [{"guess": guess_upper, "colors": colors}]
        updated_game = self.repository.update_game(
            session_id=session_id,
            remaining_attempts=remaining_attempts,
            game_status=game_status,
            guesses=new_guesses,
            player_id=game.player_id,
        )
        if updated_game is None:
            raise ValueError("Game is already finished.")

        if game_status in (STATUS_WON, STATUS_LOST) and updated_game.player_id is not None:
            self.user_repository.record_game_result(
                updated_game.player_id,
                won=game_status == STATUS_WON,
            )

        return {
            "session_id": session_id,
            "guess": guess_upper,
            "is_valid": True,
            "is_winning": is_winning,
            "colors": colors,
            "remaining_attempts": remaining_attempts,
            "game_status": game_status,
        }
