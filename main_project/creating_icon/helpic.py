import os
from PIL import Image
import win32com.client

# ==== Настройки ====
APP_NAME = r"C:\Users\School-PC\PycharmProjects\AutoSchedule\main_project\sdelalTIMOHA.exe"
ICON_PNG = "670929f5-dee4-4595-af0f-6cea63104f3b.png"                   # Путь к PNG-изображению
SHORTCUT_NAME = "School21C"        # Имя ярлыка на рабочем столе
ICON_ICO = "icon.ico"                   # Временный .ico файл


def convert_png_to_ico(png_path, ico_path):
    """Конвертирует PNG в ICO"""
    if not os.path.exists(png_path):
        print(f"[Ошибка] Файл {png_path} не найден!")
        return False

    try:
        img = Image.open(png_path)
        img = img.resize((256, 256))  # Windows предпочитает 256x256
        img.save(ico_path, format="ICO")
        print(f"[OK] Иконка сохранена как {ico_path}")
        return True
    except Exception as e:
        print(f"[Ошибка] Не удалось конвертировать изображение: {e}")
        return False


def create_shortcut(target_path, shortcut_name, icon_path=None):
    """Создаёт ярлык на рабочем столе"""
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = os.path.abspath(target_path)
    shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(target_path))
    if icon_path and os.path.exists(icon_path):
        shortcut.IconLocation = os.path.abspath(icon_path)
    shortcut.save()
    print(f"[OK] Ярлык создан на рабочем столе: {shortcut_path}")


if __name__ == "__main__":
    # Получаем текущую директорию
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, APP_NAME)
    png_icon = os.path.join(current_dir, ICON_PNG)
    ico_icon = os.path.join(current_dir, ICON_ICO)

    # Шаг 1: Конвертация PNG в ICO
    convert_png_to_ico(png_icon, ico_icon)

    # Шаг 2: Создание ярлыка
    if os.path.exists(app_path):
        create_shortcut(app_path, SHORTCUT_NAME, ico_icon)
    else:
        print(f"[Ошибка] Целевой файл {app_path} не найден!")