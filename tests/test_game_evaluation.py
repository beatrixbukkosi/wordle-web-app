"""Acceptance tests for AC1 (normal guess evaluation) and AC4 (duplicate letters)."""

import pytest

import main as game_api
from services.game_service import GameService


@pytest.mark.parametrize(
    ("guess", "target_word", "expected_colors"),
    [
        ("PAPER", "APPLE", ["YELLOW", "YELLOW", "GREEN", "YELLOW", "GRAY"]),
        ("CRANE", "SLATE", ["GRAY", "GRAY", "GREEN", "GRAY", "GREEN"]),
        ("SLATE", "SLATE", ["GREEN"] * 5),
        ("XXXXX", "APPLE", ["GRAY"] * 5),
    ],
)
def test_evaluate_guess_returns_a_color_for_each_letter(
    guess: str, target_word: str, expected_colors: list[str]
) -> None:
    """Verifies AC1: valid five-letter guesses receive Wordle colors per letter."""
    # Arrange
    game_service = GameService()

    # Act
    colors = game_service.evaluate_guess(guess, target_word)

    # Assert
    assert colors == expected_colors
    assert len(colors) == len(guess)


@pytest.mark.parametrize(
    ("target_word", "guess", "letter", "expected_colors"),
    [
        ("APPLE", "PPPPP", "P", ["GRAY", "GREEN", "GREEN", "GRAY", "GRAY"]),
        ("APPLE", "PPXPP", "P", ["YELLOW", "GREEN", "GRAY", "GRAY", "GRAY"]),
        ("BAACA", "AAAAX", "A", ["YELLOW", "GREEN", "GREEN", "GRAY", "GRAY"]),
    ],
)
def test_evaluate_guess_limits_duplicate_matches_to_target_count(
    target_word: str, guess: str, letter: str, expected_colors: list[str]
) -> None:
    """Verifies AC4: duplicate guesses prioritize exact matches and do not overcount."""
    # Arrange
    game_service = GameService()

    # Act
    colors = game_service.evaluate_guess(guess, target_word)

    # Assert
    assert colors == expected_colors
    assert sum(color != "GRAY" for color in colors) == target_word.count(letter)


def test_validate_guess_returns_colors_for_a_valid_five_letter_guess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies AC1: the validation endpoint returns per-letter statuses."""
    # Arrange
    monkeypatch.setattr(game_api.game_service, "valid_guesses", {"PAPER"})
    request = game_api.GuessRequest(guess="PAPER", target_word="APPLE")

    # Act
    response = game_api.validate_guess(request)

    # Assert
    assert response["is_valid"] is True
    assert response["colors"] == ["YELLOW", "YELLOW", "GREEN", "YELLOW", "GRAY"]


@pytest.mark.parametrize(
    ("guess", "valid_guesses", "expected"),
    [("PAPER", {"PAPER"}, True), ("XXXXX", {"PAPER"}, False), ("PAPE", {"PAPER"}, False)],
)
def test_validate_word_checks_dictionary_without_submitting_guess(
    monkeypatch: pytest.MonkeyPatch,
    guess: str,
    valid_guesses: set[str],
    expected: bool,
) -> None:
    monkeypatch.setattr(game_api.game_service, "valid_guesses", valid_guesses)

    response = game_api.validate_word(game_api.WordValidationRequest(guess=guess))

    assert response.is_valid is expected
