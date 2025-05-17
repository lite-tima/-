from PIL import Image
import os

# Путь к исходному изображению (поддерживает .png, .jpg и т.д.)
input_image = 'photo.jpg'

# Папка для выходного файла
output_folder = "../dist"
os.makedirs(output_folder, exist_ok=True)

# Путь к иконке
output_ico = os.path.join(output_folder, "../dist/schedule.ico")

# Открываем изображение
img = Image.open(input_image)

# Изменяем размер до 256x256 (если нужно)
img = img.resize((256, 256))

# Сохраняем как .ico
img.save(output_ico, format='ICO', sizes=[(256, 256)])

print(f"✅ ICO файл создан: {output_ico}")