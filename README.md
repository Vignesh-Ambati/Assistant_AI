# Assistant AI — Microservice Architecture

This project is a modern, decoupled Desktop AI Assistant. It consists of a **FastAPI backend** running in Docker and an **Electron + React frontend** acting as a lightweight desktop client.

## 🎓 Beginner Learning Guide
If you are completely new to coding, don't worry! We have created a comprehensive, beginner-friendly guide that explains every concept used in this project using simple analogies.

👉 **[Read the Beginner's Learning Guide Here](LEARNING_GUIDE.md)** 👈

---

## 🏗️ Architecture Segments

The repository is broken into three main independent segments.

### Segment 1: Global Infrastructure (Root)
This segment is responsible for defining the workspace, containerizing the application, and orchestrating services.
*   **`docker-compose.yml`**: The master orchestration file. It defines and connects 4 isolated containers:
    *   `api`: The FastAPI Python backend.
    *   `celery-worker`: A background worker for heavy tasks (like document processing).
    *   `postgres`: A PostgreSQL 16 database with the `pgvector` extension for storing chat history and embeddings.
    *   `redis`: An in-memory cache used for token bucket rate-limiting and Celery message brokering.
*   **`pyproject.toml`**: The UV workspace definition and configuration file for formatting rules (Ruff) and testing settings (Pytest).
*   **`main.py`**: Unified Python setup & launcher script. Automatically opens **Ollama** and **Docker Desktop** if they are not running, initializes `.venv` and `node_modules` if missing, boots Docker Compose, applies Alembic database migrations, and starts the desktop app.

### Segment 2: The Backend API (`/api`)
This is the "Brain" of the operation. It is a stateless Python application.
*   **`api/Dockerfile`**: A multi-stage Docker build that packages the Python app using `uv` for fast dependency resolution.
*   **`api/alembic.ini` & `api/app/db/migrations/`**: Alembic configuration. When run, this reads the python models and automatically maps them into SQL tables in PostgreSQL.
*   **`api/app/main.py`**: The FastAPI application factory. It hooks up the middleware, registers the routers, and handles the `lifespan` (booting DB connections before accepting web traffic).
*   **`api/app/routers/`**: The HTTP endpoints exposed to the frontend.
    *   `chat.py`: Handles `/chat/stream` for generating responses. Uses Server-Sent Events (SSE) to push words back to the UI one token at a time.
    *   `models.py`: Endpoints to get available AI models from Ollama.
    *   `health.py`: Diagnostics to ensure DB, Redis, and Ollama are reachable.
*   **`api/app/repositories/chat.py`**: Implementation of the *Repository Pattern*. It prevents database logic (SQLAlchemy) from leaking into the routers.
*   **`api/app/services/`**: Core business logic.
    *   `ollama.py`: Asynchronous `httpx` client to talk to the host Ollama service (`host.docker.internal:11434`).
    *   `rate_limiter.py`: A Redis-backed Sliding Window Token Bucket to prevent API spam.
*   **`api/app/models/`**:
    *   `database.py`: SQLAlchemy ORM classes (`ChatSession`, `Message`). Includes `pgvector` for future semantic search.
    *   `schemas.py`: Pydantic V2 models for strict request/response validation and OpenAPI doc generation.
*   **`api/app/dependencies.py`**: FastAPI `Depends()` injection. Yields the live Database Sessions and Redis Connections to the routers securely.
*   **`api/app/middleware/`**: ASGI middleware that intercepts requests to inject tracing headers (`X-Correlation-ID`) and measure request times (`X-Process-Time`).

### Segment 3: The Desktop Client (`/client`)
This is a desktop shell that simply renders the UI. It contains **ZERO** database or AI logic.
*   **`client/main.cjs`**: The Electron backend of the desktop app. It provides OS-level capabilities (like creating a frameless window, pinning it "Always on Top" as a widget, and enabling dragging).
*   **`client/src/`**: The React frontend code.
    *   `App.tsx`: The main chat interface. It loads your local Ollama models, manages chat messages, and reads the SSE stream from the FastAPI backend securely via buffered chunk parsing.
    *   `index.css`: Imports Tailwind CSS for rapid styling.
*   **`client/package.json`**: Defines Node.js dependencies (React, Electron, Vite, Tailwind).

---

## 🚀 Usage (`main.py`)

All setup and startup tasks are handled by **`main.py`** in the project root:

```powershell
# Full launch (starts Ollama & Docker if closed, sets up environments if missing, runs migrations, and launches Electron app)
python main.py
```

### Useful Flags
*   **`python main.py --web`**: Launch the React UI in your browser (`http://localhost:1420`) instead of booting the Electron window.
*   **`python main.py --infra-only`**: Start Ollama, Docker Desktop, backend containers, and DB migrations without opening the UI.
*   **`python main.py --setup`**: Force reinstall of `.venv` Python packages and `client/node_modules`.
*   **`python main.py --stop`**: Stop all running Docker Compose containers.
