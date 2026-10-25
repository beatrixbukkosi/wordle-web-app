# Wordle Web Application Documentation

## 1. General AI Usage
* **Tools Used:** 
  * **GitHub Copilot**
  * **Google Antigravity (Gemini)**
* **Working Method:** I used an `AGENTS.md` file in the project root to guide the AI tools. This file helps the AI understand the project architecture (FastAPI for the backend, Streamlit for the frontend) and enforces basic Clean Code rules. In practice, I interacted with the AIs using regular prompts in the chat interface. I manually reviewed their suggested solutions before accepting them. If an accepted solution later turned out to be incorrect, I iterated on the problem with further prompts. If one AI struggled to solve a specific issue, I seamlessly switched to the other tool to find a working solution.

---

## 2. AI Decision Cases

### Decision Case 1: Wordle Letter Evaluation Logic 
* **Problem & Context:** I needed to write the logic that colors the Wordle guesses (Green, Yellow, Gray). The tricky part was making sure the game doesn't give too many "Yellow" (PRESENT) colors if the player guesses a letter more times than it appears in the target word.
* **Tool Used:** Github Copilot
- **Main Prompt:** 
```text
Write a method that checks each letter in the guessed word and returns the correct color for every letter.
Follow these rules:
- GREEN (CORRECT): If a letter is in the correct position in the target word, color it green.
- YELLOW (PRESENT): If a letter exists in the target word but is in the wrong position, color it yellow.
- GRAY (ABSENT): If a letter does not exist in the target word, color it gray.

Important: Handle duplicate letters correctly.
Follow these steps in this exact order:
1. First, check all letters that are in the correct position. Mark them green and remove these letters from the remaining target letters.
2. Next, check the letters that are not green. If a letter still exists in the remaining target letters, mark it yellow and remove one occurrence of that letter from the remaining target letters.
3. If a letter does not exist in the remaining target letters, mark it gray.

Important rules:
- Always assign green letters first.
- A letter can only be yellow if there is an unused matching letter in the target word.
- Never mark more letters yellow than the target word actually contains.
- If a letter appears multiple times in the guess but fewer times in the target word, only the correct number of letters can be green or yellow. The extra letters must be gray.
- Return one color for each letter in the guessed word, in the same order.

Example:
Target word: APPLE
Guessed word: PAPER

Expected colors:
- P → Yellow
- A → Yellow
- P → Green
- E → Yellow
- R → Gray

The result should be:
[YELLOW, YELLOW, GREEN, YELLOW, GRAY]

Make sure the method works correctly for words with repeated letters and follows the same rules as the original Wordle game. 
```
* **AI Response / Implementation:** The assistant implemented `evaluate_guess` in `backend/services/game_service.py` using two passes. In the first pass it marks exact-position matches as `GREEN` and removes those letters from a list of the target's remaining letters. In the second pass it examines only non-green guess letters. If a matching letter remains, it marks that guess letter `YELLOW` and removes one occurrence, otherwise, it stays `GRAY`. This ensures duplicate letters are scored according to their available occurrences. The validation endpoint returns the color list and the frontend uses it to color the submitted tiles.
* **Decision & Reasons:** I **accepted** this implementation because it follows the requested green-first order and correctly limits yellow matches when letters are repeated. Keeping the evaluation logic in `GameService` also keeps game rules out of the FastAPI route handler.
* **Verification (Evidence):** I manually checked the example `Target="APPLE", Guess="PAPER"` and repeated-letter cases and also verified the behavior with pytest tests in `tests/test_game_evaluation.py` and `tests/test_guess_submission.py`.

---

## 3. Setup & Execution Instructions

### Prerequisites
- Python 3.10+
- `pip` package manager

### Installation
1. Clone the repository.
2. Run `pip install -r requirements.txt`.

### Running the Application
1. Start the backend: `uvicorn backend.main:app --reload`
2. Start the frontend: `streamlit run frontend/app.py`

## Running the Tests

From the project root run all tests: python -m pytest -q
