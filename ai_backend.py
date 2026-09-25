import json
import urllib.request
import urllib.error
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class AiBackend(QObject):
    """Handles communication with Ollama's local API with streaming support."""
    connection_status_changed = pyqtSignal(str)

    def __init__(self, base_url="http://localhost:11434", model_name="qwen2.5-coder:7b", parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.history = []

    def get_available_models(self):
        """Returns list of model names available in Ollama."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    return [m.get('name') for m in data.get('models', [])]
        except Exception:
            pass
        return []

    def set_model(self, model_name):
        self.model_name = model_name

    def check_connection(self):
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self.connection_status_changed.emit('connected')
                    return True
        except Exception:
            pass
        self.connection_status_changed.emit('disconnected')
        return False

    def send_message_stream(self, user_message):
        """Generator that yields response tokens one at a time (streaming)."""
        self.history.append({'role': 'user', 'content': user_message})

        url = f"{self.base_url}/api/chat"
        messages_to_send = self.history[-20:]

        payload = {
            "model": self.model_name,
            "messages": messages_to_send,
            "stream": True
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')

        full_response = ""
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get('message', {}).get('content', '')
                        if token:
                            full_response += token
                            yield token
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise Exception(f"Error: {str(e)}")

        self.history.append({'role': 'assistant', 'content': full_response})

    def clear_history(self):
        self.history.clear()


class StreamWorker(QThread):
    """Streams tokens from AI backend, emitting each token as it arrives."""
    token_received = pyqtSignal(str)
    stream_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, ai_backend, message, parent=None):
        super().__init__(parent)
        self.ai_backend = ai_backend
        self.message = message

    def run(self):
        try:
            for token in self.ai_backend.send_message_stream(self.message):
                self.token_received.emit(token)
            self.stream_finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
