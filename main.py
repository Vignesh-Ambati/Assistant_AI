import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from ai_backend import AiBackend
from chat_window import ChatWindow
from floating_button import FloatingButton

def main():
    app = QApplication(sys.argv)
    
    # Do not quit when the last window (chat window) is closed, 
    # since we have the system tray and floating button
    app.setQuitOnLastWindowClosed(False)
    
    # Print debug info
    screen = app.primaryScreen()
    geo = screen.availableGeometry()
    print(f"[INFO] Screen: {geo.width()}x{geo.height()}, Scale: {screen.devicePixelRatio()}")
    
    ai_backend = AiBackend(base_url="http://localhost:11434")
    
    chat_window = ChatWindow(ai_backend)
    
    floating_button = FloatingButton(chat_window)
    
    # Force position to be safely on-screen
    x = geo.x() + geo.width() - 75
    y = geo.y() + geo.height() - 120
    floating_button.move(x, y)
    print(f"[INFO] Button placed at ({x}, {y})")
    
    floating_button.show()
    floating_button.raise_()
    floating_button.activateWindow()
    print("[INFO] AI Assistant is running! Look for the purple circle button.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
