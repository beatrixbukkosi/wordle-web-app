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