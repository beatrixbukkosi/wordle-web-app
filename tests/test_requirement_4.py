# Test suite for AC4: Duplicate Letters


import pytest
import main as game_api
from services.game_service import GameService


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
