from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.game_service import GameService

app = FastAPI(title="Wordle API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

game_service = GameService()

@app.on_event("startup")
def startup_event():
    """Triggered when the server starts."""
    game_service.load_dictionaries()

@app.get("/api/v1/game/start")
def start_game():
    """Initializes a new game session and returns the target word."""
    try:
        target_word = game_service.get_random_word()
        return {
            "target_word": target_word,
            "word_length": len(target_word)
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

class GuessRequest(BaseModel):
    guess: str
    target_word: str | None = None

@app.post("/api/v1/game/validate")
def validate_guess(request: GuessRequest):
    """Validates if the submitted guess exists in the dictionary and checks for a win."""
    guess_upper = request.guess.upper()
    is_valid = game_service.is_valid_guess(guess_upper)
    is_winning = bool(is_valid and request.target_word and guess_upper == request.target_word.upper())
    colors = (
        game_service.evaluate_guess(guess_upper, request.target_word)
        if is_valid and request.target_word
        else None
    )
    return {
        "guess": guess_upper,
        "is_valid": is_valid,
        "is_winning": is_winning,
        "colors": colors,
    }