import subprocess
import urllib.request
import urllib.error
import json
import time
import sys
import webbrowser
import shutil

def check_ollama_installed():
    return shutil.which('ollama') is not None

def check_ollama_running():
    try:
        response = urllib.request.urlopen('http://localhost:11434', timeout=2)
        return response.getcode() == 200
    except urllib.error.URLError:
        return False

def start_ollama():
    print("Starting Ollama server...")
    try:
        subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        return check_ollama_running()
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

def check_model_available(model_name):
    try:
        req = urllib.request.Request('http://localhost:11434/api/tags')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = [model['name'] for model in data.get('models', [])]
            return any(model_name in name for name in models)
    except Exception as e:
        print(f"Error checking models: {e}")
        return False

def pull_model(model_name):
    print(f"Pulling model {model_name}... This might take a while.")
    try:
        process = subprocess.Popen(
            ['ollama', 'pull', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            print(line, end='', flush=True)
            
        process.wait()
        if process.returncode == 0:
            print(f"\nSuccessfully pulled {model_name}")
            return True
        else:
            print(f"\nFailed to pull {model_name}")
            return False
    except Exception as e:
        print(f"Error pulling model: {e}")
        return False

def main():
    model_name = 'qwen2.5-coder:7b'
    
    if not check_ollama_installed():
        print("Ollama is not installed.")
        print("Please download and install it from https://ollama.com/download/windows")
        choice = input("Open download page in browser? (y/n): ")
        if choice.lower().startswith('y'):
            webbrowser.open('https://ollama.com/download/windows')
        
        input("Press Enter after you have installed Ollama to continue...")
        if not check_ollama_installed():
            print("Ollama still not found in PATH. Please restart your terminal/computer and try again.")
            sys.exit(1)
            
    if not check_ollama_running():
        if not start_ollama():
            print("Failed to start Ollama server. Please start it manually.")
            sys.exit(1)
            
    if not check_model_available(model_name):
        if not pull_model(model_name):
            print(f"Failed to pull {model_name}. Please try running 'ollama pull {model_name}' manually.")
            sys.exit(1)
            
    print(f"Setup complete! Ollama is running and {model_name} is ready.")

if __name__ == '__main__':
    main()
