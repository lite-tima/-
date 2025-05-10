import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QCheckBox
from PyQt6.QtCore import Qt
import sqlite3
bd = sqlite3.connect('BD.db') #сама база данных
cursor = bd.cursor()
class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.is_admin = False

    def get_is_admin(self):
        '''возращает статус админа/юзера'''
        if self.is_admin:
            return 'admin'
        else:
            return 'user'

    def __str__(self):
        return f"User      (username='{self.username}')"

class Active:
    def __init__(self, bd):
        self.bd = bd  # база данных
        self.cursor = self.bd.cursor()
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER
                )
                ''')

    def login(self, username, password):
        # Проверка, существует ли пользователь и совпадает ли пароль
        self.cursor.execute(f'SELECT * FROM Users WHERE username = "{username}"')
        users = self.cursor.fetchall()
        self.bd.commit()
        # Проверка пароля
        if users == []:
            return False, "Такого пользователя нет в базе данных!\nЗарегистрируйтесь!"
        if password == users[0][2]:
            return True, "Успешный вход!"
        else:
            return False, "Пароль не совпадает. Пожалуйста, попробуйте снова."#Пароль не совпадает
        return None, "Пользователь не найден. Пожалуйста, зарегистрируйтесь." #Пароль не найден

    def register(self, username, password):
        # проверка на существование такого логина
        self.cursor.execute(f'SELECT * FROM Users WHERE username = "{username}"')
        users = self.cursor.fetchall()
        self.bd.commit()
        #Если таких пользователей еще нет
        if users == []:
            self.cursor.execute('INSERT INTO Users(username, password, is_admin) VALUES (?, ?, ?)', (username, password, False))
            self.bd.commit()
            return True, "Успешная регистрация"
        #Иначе
        else:
            return False, "Данный логин занят другим пользователем. Введите другой"

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()  # Вызываем конструктор родительского класса QWidget
        self.setWindowTitle("Вход")  # Устанавливаем заголовок окна
        self.setGeometry(600, 340, 280, 150)  # Устанавливаем размеры и положение окна (x, y, ширина, высота)
        bd = sqlite3.connect('BD.db')  # Подключаемся к базе данных SQLite
        self.active = Active(bd)  # Создаем экземпляр класса Active, который управляет взаимодействием с базой данных

        layout = QVBoxLayout()  # Создаем вертикальный layout для расположения элементов управления

        # Создаем и настраиваем поле для ввода логина
        self.username_label = QLabel("Логин:")  # Метка для поля ввода логина
        self.username_input = QLineEdit()  # Поле ввода для логина
        layout.addWidget(self.username_label)  # Добавляем метку в layout
        layout.addWidget(self.username_input)  # Добавляем поле ввода в layout

        # Создаем и настраиваем поле для ввода пароля
        self.password_label = QLabel("Пароль:")  # Метка для поля ввода пароля
        self.password_input = QLineEdit()  # Поле ввода для пароля
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)  # Устанавливаем режим скрытого ввода для пароля
        layout.addWidget(self.password_label)  # Добавляем метку в layout
        layout.addWidget(self.password_input)  # Добавляем поле ввода в layout

        # Создаем чекбокс для запоминания пользователя
        self.remember_me_checkbox = QCheckBox("Запомнить меня")  # Чекбокс для опции "Запомнить меня"
        layout.addWidget(self.remember_me_checkbox)  # Добавляем чекбокс в layout

        # Создаем кнопку для входа
        self.login_button = QPushButton("Вход")  # Кнопка для выполнения входа
        self.login_button.clicked.connect(self.handle_login)  # Подключаем обработчик нажатия кнопки
        layout.addWidget(self.login_button)  # Добавляем кнопку в layout

        # Создаем кнопку для регистрации
        self.register_button = QPushButton("Регистрация")  # Кнопка для выполнения регистрации
        self.register_button.clicked.connect(self.handle_register)  # Подключаем обработчик нажатия кнопки
        layout.addWidget(self.register_button)  # Добавляем кнопку в layout

        self.setLayout(layout)  # Устанавливаем созданный layout для текущего окна

    def keyPressEvent(self, event):
        # Обработка нажатий клавиш
        if event.key() == Qt.Key.Key_Return:  # Если нажата клавиша Enter
            if self.username_input.hasFocus():  # Если фокус на поле ввода логина
                self.password_input.setFocus()  # Устанавливаем фокус на поле ввода пароля
            elif self.password_input.hasFocus():  # Если фокус на поле ввода пароля
                self.handle_login()  # Вызываем метод для обработки входа

    def handle_login(self):
        # Обработка логики входа
        username = self.username_input.text()  # Получаем текст из поля ввода логина
        password = self.password_input.text()  # Получаем текст из поля ввода пароля

        # Проверка на пустые поля ввода
        if not username or not password:  # Если одно из полей пустое
            QMessageBox.warning(self, "Input Error", "Пожалуйста, введите имя пользователя и пароль.")  # Показываем предупреждение
            return  # Завершаем выполнение метода

        # Используем метод класса Active для входа
        login_result, message = self.active.login(username, password)  # Пытаемся выполнить вход
        if login_result is True:  # Если вход успешен
            # Проверка состояния чекбокса "Запомнить меня"
            if self.remember_me_checkbox.isChecked():  # Если чекбокс отмечен
                QMessageBox.information(self, "User  Info", f"Вход выполнен: {username}\nПароль будет запомнен.")  # Показываем сообщение о запоминании пароля
            else:
                QMessageBox.information(self, "User  Info", f"Вход выполнен: {username}\nПароль не будет запомнен.")  # Показываем сообщение о том, что пароль не запомнен
        else:
            QMessageBox.warning(self, "Login Error", message)  # Показываем сообщение об ошибке входа

    def handle_register(self):
        # Обработка логики регистрации
        username = self.username_input.text()  # Получаем текст из поля ввода логина
        password = self.password_input.text()  # Получаем текст из поля ввода пароля

        # Проверка на пустые поля ввода
        if not username or not password:  # Если одно из полей пустое
            QMessageBox.warning(self, "Input Error", "Пожалуйста, введите имя пользователя и пароль.")  # Показываем предупреждение
            return  # Завершаем выполнение метода

        # Используем метод класса Active для регистрации
        register_result, message = self.active.register(username, password)  # Пытаемся зарегистрировать пользователя
        QMessageBox.information(self, "Registration", message)  # Показываем сообщение о результате регистрации

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
