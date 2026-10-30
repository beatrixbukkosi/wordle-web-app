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
Before starting the refactoring, please read the AGENTS.md file in the project root and strictly adhere to its architectural guidelines, coding standards, and project constraints.
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

### Decision Case 2: Server-side Session Management & Page Reload Persistence (AI Tool Comparison)
- **Problem & Context:** In the initial prototype, the target secret word was stored in client-side state (`st.session_state`), sent to the backend during each guess submission, and explicitly rendered in the frontend debug menu. Furthermore, refreshing the browser (F5) cleared the in-memory state and lost the ongoing game session. To enforce backend state authority (AC #8 - State Management & Persistence) and prevent client-side secret leakage, I needed to refactor the architecture so the backend acts as the single source of truth using a session identifier (`session_id`), syncs with the Streamlit URL query parameters (`st.query_params`), and logs the secret word strictly on the backend console for developer debugging.
- **Tools Used & Comparison:** GitHub Copilot (GPT-6-Luna) vs. Google Antigravity (Gemini 3.8 Flash).
  - **Tool A (GitHub Copilot / GPT-6-Luna):** Modified 10 files (+589 / -150 lines). It refactored the application to use raw Python `sqlite3` queries inside a `GameRepository` class. It successfully separated the client from the target word and introduced `st.query_params` sync. However, it used a `GET` endpoint (`GET /api/v1/game/start`) for creating new game resources, which strays from standard REST conventions (`POST`), and wrote raw SQL queries instead of using an ORM framework.
  - **Tool B (Google Antigravity / Gemini 3.8 Flash):** Modified 14 files (+1263 / -344 lines). It implemented a robust SQLAlchemy ORM persistent database layer (`data/wordle_games.sqlite3`) and strictly adhered to the project's `AGENTS.md` clean architecture guidelines. It introduced strong Pydantic DTO schemas (`GameStartResponse`, `GameStateResponse`, `GuessRequest`, `GuessResponse`), utilized modern FastAPI `lifespan` event handlers, applied Streamlit event-driven callback handlers (`on_click`), and also generated 22 comprehensive automated tests (including isolated session management and frontend URL restoration tests).
- **Main Prompt:**
```text
Before starting the refactoring, please read the AGENTS.md file in the project root and strictly adhere to its architectural guidelines, coding standards, and project constraints.
Refactor the game and session management of the Wordle application in both the backend and the Streamlit frontend based on the following requirements:
1. Server-side State Management & Session Persistence:
   - When starting a new game, the backend must generate a unique session identifier (session_id).
   - The complete game state (secret word, previous guesses, remaining attempts, game status) must be stored on the backend side and be queryable using the session_id.
   - Ensure that upon browser refresh (F5), the Streamlit frontend can restore the active state from the server using the session_id stored in the URL, preventing an ongoing game from being lost.
2. Security & Developer Testability:
   - The backend must NEVER return the secret word to the frontend (remove the secret_word field from all client-facing API responses).
   - To facilitate manual testing, when a new game starts, the backend must log the selected secret word along with its session_id to the console/terminal so it remains visible during development.
Please do the necessary backend (FastAPI) and frontend (Streamlit) code modifications.
```
- **Decision & Reasons:** I **accepted Google Antigravity's (Gemini 3.8 Flash)** implementation and rejected GitHub Copilot's solution. Although Gemini modified twice as much code (~1,200+ lines vs. ~500 lines), its output was significantly higher quality: it strictly adhered to `AGENTS.md` by using SQLAlchemy ORM instead of raw SQL queries, correctly used `POST` instead of `GET` for starting games, applied clean Streamlit event callbacks, and provided robust Pydantic schemas that guaranteed the `secret_word` was omitted from client-facing API responses.
- **Verification (Evidence):** I manually tested browser refreshes (F5) to verify state restoration via `st.query_params`, checked `uvicorn` console logs for secret word logging, and ran automated tests using pytest (`python -m pytest -q`), where all 22 tests passed across `test_session_management.py`, `test_frontend_state.py`, `test_game_evaluation.py`, and `test_guess_submission.py`.
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
