"""Unified launcher and setup manager for Assistant AI.

Replaces all .bat scripts (01_start_infrastructure, 02_setup_api,
03_setup_client, 04_run_app) with a single Python entrypoint that:
1. Automatically opens & starts Ollama if it is not running.
2. Automatically opens & starts Docker Desktop if it is not running.
3. Sets up the Python (.venv) and Client (node_modules) environments if needed.
4. Boots the Docker Compose infrastructure and runs Alembic DB migrations.
5. Launches the Tauri desktop client (or Vite web client with --web).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT_DIR = Path(__file__).resolve().parent
CLIENT_DIR = ROOT_DIR / "client"
VENV_DIR = ROOT_DIR / ".venv"

OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"
API_HEALTH_URL = "http://localhost:8000/health"


def banner(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def is_url_reachable(url: str, timeout: float = 2.0) -> bool:
    """Return True if an HTTP GET to `url` succeeds with status 200."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def launch_detached(cmd: list[str]) -> None:
    """Launch a background GUI/daemon process detached from the current console."""
    if sys.platform == "win32":
        creationflags = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        )
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    else:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )


def ensure_ollama_running(timeout_seconds: int = 60) -> None:
    """Check if Ollama is running; if not, open Ollama and wait until ready."""
    banner("Step 1/5: Checking Ollama Service")

    if is_url_reachable(OLLAMA_HEALTH_URL):
        print("[OK] Ollama is already running at http://localhost:11434")
        return

    print("[INFO] Ollama is not running. Attempting to start Ollama...")

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    ollama_app_candidates = [
        Path(local_app_data) / "Programs" / "Ollama" / "Ollama app.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "Ollama app.exe",
    ]
    ollama_cli = shutil.which("ollama") or str(
        Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
    )

    started = False
    for app_path in ollama_app_candidates:
        if app_path.is_file():
            print(f"[INFO] Launching Ollama Desktop App: {app_path}")
            launch_detached([str(app_path)])
            started = True
            break

    if not started:
        if Path(ollama_cli).is_file() or shutil.which("ollama"):
            print(f"[INFO] Starting Ollama server via CLI: {ollama_cli} serve")
            launch_detached([ollama_cli, "serve"])
            started = True
        else:
            print(
                "[ERROR] Could not find Ollama installed on this system.\n"
                "        Please install Ollama from https://ollama.com"
            )
            sys.exit(1)

    print("[WAIT] Waiting for Ollama API (http://localhost:11434) to become ready...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_url_reachable(OLLAMA_HEALTH_URL):
            print("[OK] Ollama is now running and ready!")
            return
        time.sleep(2)

    print("[ERROR] Timed out waiting for Ollama to start.")
    sys.exit(1)


def is_docker_running() -> bool:
    """Return True if the Docker daemon is responsive."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def ensure_docker_running(timeout_seconds: int = 120) -> None:
    """Check if Docker Desktop is running; if not, launch it and wait for the daemon."""
    banner("Step 2/5: Checking Docker Desktop")

    if is_docker_running():
        print("[OK] Docker Engine is already running.")
        return

    print("[INFO] Docker Engine is not running. Attempting to open Docker Desktop...")

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    docker_candidates = [
        Path(program_files) / "Docker" / "Docker" / "Docker Desktop.exe",
        Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe"),
        Path(local_app_data) / "Docker" / "Docker Desktop.exe",
    ]

    launched = False
    for exe_path in docker_candidates:
        if exe_path.is_file():
            print(f"[INFO] Launching Docker Desktop: {exe_path}")
            launch_detached([str(exe_path)])
            launched = True
            break

    if not launched:
        print(
            "[ERROR] Could not find 'Docker Desktop.exe'.\n"
            "        Please install or start Docker Desktop manually."
        )
        sys.exit(1)

    print("[WAIT] Waiting for Docker Desktop engine to initialize (this may take 30-60s)...")
    deadline = time.time() + timeout_seconds
    elapsed = 0
    while time.time() < deadline:
        if is_docker_running():
            print("[OK] Docker Desktop is now running and ready!")
            return
        time.sleep(3)
        elapsed += 3
        if elapsed % 9 == 0:
            print(f"       Still waiting for Docker daemon... ({elapsed}s elapsed)")

    print("[ERROR] Timed out waiting for Docker Desktop to start.")
    sys.exit(1)


def setup_python_env(force: bool = False) -> None:
    """Create .venv and install Python dependencies using uv (replaces 02_setup_api.bat)."""
    banner("Step 3/5: Checking Python Environment (.venv)")

    if not shutil.which("uv"):
        print("[WARN] 'uv' not found on PATH; skipping local .venv setup (Docker handles API runtime).")
        return

    venv_python = (
        VENV_DIR / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else VENV_DIR / "bin" / "python"
    )

    if not venv_python.exists():
        print("[INFO] Creating virtual environment (.venv)...")
        subprocess.run(["uv", "venv"], cwd=ROOT_DIR, check=True)
        force = True

    marker_file = VENV_DIR / ".installed_ok"
    if force or not marker_file.exists():
        print("[INFO] Installing Python API dependencies into .venv...")
        subprocess.run(["uv", "pip", "install", "-e", ".[dev]"], cwd=ROOT_DIR, check=True)
        marker_file.write_text("installed\n", encoding="utf-8")
        print("[OK] Python environment setup complete!")
    else:
        print("[OK] Python .venv already configured (use --setup to force reinstall).")


def setup_client_env(force: bool = False) -> None:
    """Install frontend npm packages in client/ (replaces 03_setup_client.bat)."""
    banner("Step 4/5: Checking Client Environment (React + Tauri)")

    if not CLIENT_DIR.exists():
        print(f"[ERROR] Client directory not found at {CLIENT_DIR}")
        sys.exit(1)

    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        print("[ERROR] 'npm' (Node.js) is not installed or not on PATH.")
        sys.exit(1)

    node_modules = CLIENT_DIR / "node_modules"
    if force or not node_modules.exists():
        print("[INFO] Running 'npm install' in client/...")
        subprocess.run([npm_cmd, "install"], cwd=CLIENT_DIR, check=True)
        print("[OK] Client node_modules installed successfully!")
    else:
        print("[OK] Client node_modules already installed (use --setup to force reinstall).")


def start_infrastructure() -> None:
    """Start Docker Compose containers and run Alembic migrations (replaces 01_start_infrastructure.bat)."""
    banner("Step 5/5: Starting Backend Infrastructure & Database Migrations")

    print("[INFO] Starting PostgreSQL, Redis, Celery Worker, and FastAPI containers...")
    subprocess.run(
        ["docker", "compose", "up", "-d", "--build", "--remove-orphans"],
        cwd=ROOT_DIR,
        check=True,
    )

    print("[INFO] Running Alembic database migrations...")
    subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "assistant", "-d", "assistant_ai", "-c", "CREATE EXTENSION IF NOT EXISTS vector;"],
        cwd=ROOT_DIR, check=False
    )
    for attempt in range(1, 6):
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "api", "alembic", "-c", "api/alembic.ini", "upgrade", "head"],
            cwd=ROOT_DIR,
            check=False,
        )
        if result.returncode == 0:
            break
        print(f"[WAIT] Waiting for database/API container to be ready (attempt {attempt}/5)...")
        time.sleep(3)
    else:
        print("[ERROR] Alembic database migration failed.")
        sys.exit(1)

    print("[WAIT] Verifying FastAPI health endpoint (http://localhost:8000/health)...")
    for _ in range(15):
        if is_url_reachable(API_HEALTH_URL):
            print("[OK] Backend API is healthy! Swagger Docs: http://localhost:8000/docs")
            return
        time.sleep(1)

    print("[WARN] Backend started, but health check did not respond within 15s.")


def stop_infrastructure() -> None:
    """Stop all running Docker Compose containers."""
    banner("Stopping Docker Infrastructure")
    subprocess.run(["docker", "compose", "down"], cwd=ROOT_DIR, check=True)
    print("[OK] Docker containers stopped.")


def run_app(web_only: bool = False) -> None:
    """Launch the Electron desktop app or Vite dev server."""
    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        print("[ERROR] 'npm' not found on PATH.")
        sys.exit(1)

    if web_only:
        banner("Launching Web Client (http://localhost:1420)")
        subprocess.run([npm_cmd, "run", "dev"], cwd=CLIENT_DIR, check=True)
    else:
        banner("Launching Electron Desktop Application")
        subprocess.run([npm_cmd, "run", "desktop"], cwd=CLIENT_DIR, check=True)


def parse_args() -> argparse.Namespace:
    """Parse command-line options for main.py."""
    parser = argparse.ArgumentParser(
        description="Unified setup & launcher for Assistant AI."
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Force re-running Python (.venv) and Client (npm install) dependency setup.",
    )
    parser.add_argument(
        "--infra-only",
        action="store_true",
        help="Only start Ollama, Docker Desktop, and backend containers without opening the UI.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Run the React frontend in browser mode (http://localhost:1420) instead of Tauri desktop.",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop all running Docker Compose containers and exit.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.stop:
        stop_infrastructure()
        return

    try:
        ensure_ollama_running()
        ensure_docker_running()
        setup_python_env(force=args.setup)
        setup_client_env(force=args.setup)
        start_infrastructure()

        if args.infra_only:
            print("\n[DONE] All infrastructure services are up and running!")
            return

        run_app(web_only=args.web)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down launcher...")
    except subprocess.CalledProcessError as exc:
        print(f"\n[ERROR] Command failed with exit code {exc.returncode}: {exc.cmd}")
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
