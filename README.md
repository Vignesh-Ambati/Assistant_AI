# 🤖 AI Desktop Assistant

A floating on-screen AI assistant button (inspired by ASUS ScreenXpert) powered by a local AI model.

![Screenshot](screenshot_placeholder.png)

## Features

- **Floating draggable button:** Always on top, providing quick access.
- **Modern dark-themed chat interface:** Clean and responsive UI.
- **Local AI processing:** Powered by Ollama (no cloud, full privacy).
- **System tray integration:** Easy management and quick access.
- **Conversation history:** Keeps track of your chats.
- **Smooth animations:** Polished user experience.

## Prerequisites

- Python 3.10+
- Windows 10/11

## Quick Start

The easiest way to start is:
1. Double-click `run.bat` in the `ai_assistant` directory. (This handles dependencies, Ollama setup, and launches the app)

**OR (Manual setup)**
1. `pip install -r ai_assistant/requirements.txt`
2. `cd ai_assistant && python setup_model.py`
3. `cd ai_assistant && python main.py`

## How it works

This assistant uses **Ollama** running locally on your machine to host the **phi3:mini** model. It provides completely private, offline AI responses without relying on cloud APIs.

## Usage

- **Drag:** Click and drag the floating button to move it around your screen.
- **Chat:** Click the button to open the chat window.
- **Right-click:** Access the menu on the floating button.
- **System Tray:** Use the system tray icon to show/hide the app or quit.

## Configuration

You can change the AI model or port in the configuration files if you prefer something other than `phi3:mini` or the default `11434` port for Ollama.

## Architecture

- `ai_assistant/setup_model.py`: Bootstraps Ollama and downloads the required model.
- `ai_assistant/run.bat`: Easy launcher script.
- `ai_assistant/main.py`: Main application (to be implemented).
- `ai_assistant/requirements.txt`: Python dependencies.

## License

MIT
