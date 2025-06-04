from registration import LoginWindow
import sys
from PyQt6.QtWidgets import (
    QApplication
)
import os
import win32com.client

def create_desktop_shortcut(icon_path, app_name):
    """последняя функция добавляет иконку"""
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop, "School21C.lnk")

    # Проверяем, существует ли уже ярлык
    if os.path.exists(shortcut_path):
        return

    path_to_exe = os.path.join(os.path.dirname(sys.executable), app_name)
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = path_to_exe
    shortcut.WorkingDirectory = os.path.dirname(path_to_exe)
    shortcut.IconLocation = os.path.abspath(icon_path)
    shortcut.save()
if __name__ == "__main__":
    create_desktop_shortcut('..dist\schedule.ico', "..\dist\A_file.exe")
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())