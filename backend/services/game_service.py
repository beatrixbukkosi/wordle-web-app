import random
import os

class GameService:
    def __init__(self):
        self.answers = []
        self.valid_guesses = set()

    def load_dictionaries(self):
        """Loads the word lists into memory."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        
        answers_path = os.path.join(project_root, "data", "target-wordle-words.txt")
        guesses_path = os.path.join(project_root, "data", "valid-wordle-words.txt")
        
        try:
            with open(answers_path, "r", encoding="utf-8") as f:
                self.answers = [line.strip().upper() for line in f if line.strip()]
                
            with open(guesses_path, "r", encoding="utf-8") as f:
                self.valid_guesses = {line.strip().upper() for line in f if line.strip()}
                
            self.valid_guesses.update(self.answers)
            print(f"GameService initialized: {len(self.answers)} answers, {len(self.valid_guesses)} valid guesses.")
        except FileNotFoundError as e:
            print(f"Dictionary initialization failed: {e}")

    def get_random_word(self) -> str:
        """Returns a random word from the answers list."""
        if not self.answers:
            raise ValueError("Dictionaries not loaded properly.")
        return random.choice(self.answers)

    def is_valid_guess(self, guess: str) -> bool:
        """Checks if the guess exists in the valid dictionary."""
        return guess.upper() in self.valid_guesses