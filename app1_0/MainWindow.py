from AddTableWindow import *
from DeleteTableDialog import *
from EditTableDialog import *


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_dialog = None
        self.init_ui()

    def init_ui(self):
        """Инициализация главного окна"""
        self.setWindowTitle("Программа администратора")
        self.setFixedSize(400, 300)


        self.main_button = StyledButton("Возможности администратора")
        self.main_button.clicked.connect(self.show_admin_options)

        layout = QVBoxLayout()
        layout.addWidget(self.main_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #E9967A;
                font-size: 14px;
            }
            QDialog {
                border: 1px solid #E9967A;
            }
        """)

    def show_admin_options(self):
        """Окно с опциями администратора"""
        if self.current_dialog:
            self.current_dialog.close()

        dialog = QDialog(self)
        self.current_dialog = dialog
        dialog.setWindowTitle("Возможности администратора")
        dialog.setFixedSize(500, 150)

        layout = QHBoxLayout()


        button_placeholder = StyledButton("Функции в разработке")
        button_tables = StyledButton("Работа с таблицами")
        button_tables.clicked.connect(lambda: self.show_table_options(dialog))

        layout.addWidget(button_placeholder)
        layout.addWidget(button_tables)

        dialog.setLayout(layout)
        dialog.exec()

    def show_table_options(self, parent_dialog):
        """Окно работы с таблицами"""
        if parent_dialog:
            parent_dialog.close()

        dialog = QDialog(self)
        self.current_dialog = dialog
        dialog.setWindowTitle("Управление таблицами")
        dialog.setFixedSize(350, 200)

        layout = QGridLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        add_btn = StyledButton("Добавить")
        add_btn.clicked.connect(lambda: self.add_record(dialog))
        layout.addWidget(add_btn, 0, 0)

        edit_btn = StyledButton("Изменить")
        edit_btn.clicked.connect(self.edit_record)
        layout.addWidget(edit_btn, 0, 1)

        update_btn = StyledButton("Удалить")
        update_btn.clicked.connect(self.update_table)
        layout.addWidget(update_btn, 1, 0, 1, 2, Qt.AlignmentFlag.AlignHCenter)

        dialog.setLayout(layout)
        dialog.exec()


    def remove_column_row(self, widget):
        """Удаляет строку столбца с подтверждением"""
        # Получаем название столбца для сообщения
        column_name = ""
        for i in range(widget.layout().count()):
            child = widget.layout().itemAt(i).widget()
            if isinstance(child, QLineEdit):
                column_name = child.text()
                break

        # Формируем текст подтверждения
        confirm_text = f"Вы действительно хотите удалить столбец '{column_name}'?" if column_name else "Вы действительно хотите удалить этот столбец?"
        confirm_text += "\nЭто действие нельзя отменить!"


        # Создаем кастомное окно подтверждения
        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle("Подтверждение удаления")
        confirm_box.setText(confirm_text)
        confirm_box.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)

        # Стилизуем окно подтверждения
        confirm_box.setStyleSheet("""
            QMessageBox {
                background-color: #1E1E1E;
                color: #E9967A;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                min-width: 80px;
                min-height: 25px;
                background-color: #252525;
                color: #E9967A;
                border: 1px solid #E9967A;
            }
        """)

        # Показываем окно и обрабатываем результат
        if confirm_box.exec() == QMessageBox.StandardButton.Yes:
            self.edit_layout.removeWidget(widget)
            widget.deleteLater()

            # Показываем сообщение об успешном удалении, если было имя столбца
            if column_name:
                QMessageBox.information(
                    self,
                    "Столбец удален",
                    f"Столбец '{column_name}' был помечен для удаления.\nИзменения применятся после сохранения.",
                    QMessageBox.StandardButton.Ok
                )

    def add_record(self, parent_dialog):
        """Обработчик кнопки 'Добавить'"""
        if parent_dialog:
            parent_dialog.close()

        dialog = AddTableWindow(self)
        self.current_dialog = dialog

        if dialog.exec() == QDialog.DialogCode.Accepted:
            inputs = dialog.get_inputs()

            if not inputs["table_name"]:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Название таблицы не может быть пустым",
                    QMessageBox.StandardButton.Ok
                )
                return

            empty_columns = [col[0] for col in inputs["columns"] if not col[1]]
            if empty_columns:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Следующие столбцы не имеют названия: {', '.join(empty_columns)}",
                    QMessageBox.StandardButton.Ok
                )
                return

            # Создание таблицы через метод AddTableWindow
            success = dialog.create_table_in_db()

            if success:
                # Формируем информацию для сообщения
                columns_info = "\n".join([f"{col[0]}: {col[1]} ({col[2]})"
                                          for col in inputs["columns"]])

                relations_info = ""
                if inputs["relations"]:
                    relations_info = "\n\nСвязи:\n" + "\n".join(
                        [f"{rel['column']} → {rel['foreign_table']}.{rel['foreign_column']}"
                         for rel in inputs["relations"]]
                    )

                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Создана таблица: {inputs['table_name']}\n\n"
                    f"Столбцы:\n{columns_info}"
                    f"{relations_info}",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось создать таблицу в базе данных",
                    QMessageBox.StandardButton.Ok
                )
    def edit_record(self):
        """Обработчик кнопки 'Изменить' - открывает диалог редактирования таблиц"""
        if self.current_dialog:
            self.current_dialog.close()

        # Проверяем, есть ли таблицы в базе данных
        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            conn.close()

            if not tables:
                QMessageBox.information(
                    self,
                    "Нет таблиц",
                    "В базе данных нет таблиц для редактирования.\nСначала создайте таблицу.",
                    QMessageBox.StandardButton.Ok
                )
                return
        except sqlite3.Error as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось проверить существующие таблицы:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )
            return

        # Создаем и показываем диалог редактирования
        dialog = EditTableDialog(self)
        self.current_dialog = dialog

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Получаем имя таблицы, которую редактировали
            edited_table = dialog.table_combo.currentText()

            QMessageBox.information(
                self,
                "Изменения сохранены",
                f"Структура таблицы '{edited_table}' была успешно изменена.",
                QMessageBox.StandardButton.Ok
            )

    def update_table(self):
        """Обработчик кнопки 'Удалить'"""
        if self.current_dialog:
            self.current_dialog.close()

        dialog = DeleteTableDialog(self)
        self.current_dialog = dialog

        if dialog.exec() == QDialog.DialogCode.Accepted:
            table_name = dialog.table_combo.currentText()
            # Здесь будет передача команды на удаление таблицы в БД
            QMessageBox.information(
                self,
                "Таблица удалена",
                f"Таблица '{table_name}' была удалена.",
                QMessageBox.StandardButton.Ok
            )
