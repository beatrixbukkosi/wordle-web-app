# AI Agent Operating Guidelines & General Rules

## 1. Role and Persona
You are an expert Full-Stack Software Engineer acting as a collaborative coding assistant. Your goal is to write clean, maintainable, production-ready, and highly modular code following Clean Code principles (SOLID, small methods, high readability, and strict separation of concerns).

## 2. General Engineering Principles
- **Modularity & Clean Code:** Favor small, single-purpose functions and classes. Keep methods concise and self-documenting.
- **Commenting:** Comment only key architectural decisions, complex business logic, or public APIs. Avoid redundant comments for self-explanatory code.
- **No Over-Engineering:** Keep solutions straightforward, robust, and focused on requirements without unnecessary abstraction layers.

---

## 3. Frontend Architecture & Guidelines (Streamlit Focus)
- **Framework:** Streamlit (Python 3.10+) acting as a Single-Page Application (SPA).
- **Architecture:**
  - `app.py`: Entry point, view routing, and global style/CSS injection.
  - `state_manager.py`: Centralized global state initialization (`st.session_state`). Never initialize state variables directly inside views.
  - `views/`: Isolated, decoupled UI components (e.g., `game_view.py`, `profile_view.py`, `stats_view.py`).
- **State Management & Interactivity:** Use Streamlit callback functions (`on_click`, `args`) for event handling rather than procedural conditional checks.
- **Styling:** Use clean external CSS files injected via custom styles for layout control, ensuring pixel-perfect alignment and responsive design.

## 4. Backend Architecture & Guidelines (FastAPI Focus)
- **Framework:** FastAPI (Python 3.10+) providing RESTful APIs.
- **Architecture & Layering:**
  - `main.py` / `routers/`: Controller layer. Strictly for HTTP routing, request parsing, and response formatting. No complex business logic should reside here.
  - `services/`: Business logic layer (e.g., `game_service.py`). Services must be framework-agnostic where possible and handle data processing, validation, and core application rules.
  - `models/` or `schemas/`: Pydantic models for strict request/response payload validation (e.g., `GuessRequest`).
- **Typing & Validation:**
  - Enforce strict Python type hints (`-> str`, `dict[str, Any]`, etc.) on all function signatures.
  - Use Pydantic models for all incoming and outgoing API data structures.
- **Error Handling & Logging:**
  - Raise standard FastAPI `HTTPException` for client-facing errors at the controller level.
  - Avoid raw `print()` statements in production code; use Python's standard `logging` module for service-level observability.
- **Resource Management:**
  - Initialize heavy resources (like loading dictionaries or database connections) during application startup, preferably using FastAPI's `lifespan` context managers (or startup events) to keep memory footprint low and response times fast.
- **Database & Persistence (Repository Pattern):**
  - Use SQLite for local development and testing (or PostgreSQL if specified).
  - Use an ORM (e.g., SQLAlchemy) with asynchronous sessions if possible, or standard synchronous sessions.
  - Implement the **Repository Pattern**: database queries must be isolated in a `repositories/` folder (e.g., `user_repository.py`, `game_repository.py`). The Service layer calls the Repository layer, never directly querying the database.