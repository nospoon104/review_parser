from pathlib import Path
import sys
import os
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import scripts.parse_reviews as parse_reviews_module
from scripts.parse_reviews import main as parse_reviews_main
from scripts.load_reviews_to_excel import main as load_reviews_to_excel_main


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()

INPUT_DIR = BASE_DIR / "ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ"
OUTPUT_DIR = BASE_DIR / "ГОТОВЫЙ_РЕЗУЛЬТАТ"
TEMPLATE_DIR = BASE_DIR / "ШАБЛОН_НЕ_ТРОГАТЬ"

INPUT_FILE = INPUT_DIR / "raw_reviews.txt"
TEMPLATE_FILE = TEMPLATE_DIR / "feedback_template.xlsx"

CAFE_OPTIONS = [
    "АндерСон Таганская 36",
    "АндерСон Авеню",
    "АндерСон Братиславская",
    "АндерСон Бутово",
    "АндерСон Гагаринский",
    "АндерСон Гиляровского",
    "АндерСон Домодедово",
    "АндерСон Кусковская",
    "АндерСон Каскад",
    "АндерСон Медведково",
    "АндерСон Мичуринский",
    "АндерСон Обручева",
    "АндерСон Островитянова",
    "АндерСон Сокол",
    "АндерСон Царицыно",
]


def get_open_command(path: Path) -> str:
    path_str = str(path)
    if os.name == "nt":
        return path_str
    if sys.platform == "darwin":
        return f'open "{path_str}"'
    return f'xdg-open "{path_str}"'


def ensure_directories():
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMPLATE_DIR.mkdir(exist_ok=True)


def validate_files_for_gui():
    if not TEMPLATE_FILE.exists():
        return (
            False,
            "Ошибка: не найден шаблон feedback_template.xlsx\n"
            f"Ожидаемый путь:\n{TEMPLATE_FILE}\n\n"
            "Проверь, что шаблон лежит в папке 'ШАБЛОН_НЕ_ТРОГАТЬ'.",
        )
    return True, ""


def save_input_text(raw_text: str):
    INPUT_FILE.write_text(raw_text, encoding="utf-8")


def open_output_folder():
    try:
        if os.name == "nt":
            os.startfile(OUTPUT_DIR)
        elif sys.platform == "darwin":
            os.system(f'open "{OUTPUT_DIR}"')
        else:
            os.system(f'xdg-open "{OUTPUT_DIR}"')
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть папку результата:\n{e}")


def run_pipeline(log_callback):
    log_callback("[1/3] Проверка папок и файлов...")
    ensure_directories()

    valid, error_text = validate_files_for_gui()
    if not valid:
        log_callback(error_text)
        return False

    log_callback("[2/3] Анализ и парсинг отзывов...")
    parse_result = parse_reviews_main()
    if parse_result != 0:
        log_callback("Ошибка на этапе парсинга отзывов.")
        return False
    log_callback("Парсинг завершён успешно.")

    log_callback("[3/3] Формирование Excel-файла...")
    excel_result = load_reviews_to_excel_main()
    if excel_result != 0:
        log_callback("Ошибка на этапе формирования Excel.")
        return False
    log_callback("Excel-файл сформирован успешно.")

    log_callback("")
    log_callback("Обработка завершена успешно.")
    log_callback(f"Результат лежит в папке:\n{OUTPUT_DIR}")
    return True


def main():
    ensure_directories()

    root = tk.Tk()
    root.title("Автоматическая обработка отзывов")
    root.geometry("1000x900")
    root.minsize(900, 700)

    title_label = tk.Label(
        root,
        text="Автоматическая обработка отзывов для кафе",
        font=("Arial", 18, "bold"),
    )
    title_label.pack(pady=(15, 10))

    instruction_text = (
        "1. Выберите своё кафе из списка.\n"
        "2. Скопируйте сырой текст сообщений из Telegram.\n"
        "3. Вставьте его в большое поле ниже.\n"
        "4. Нажмите кнопку 'Запустить обработку'.\n"
        "5. После завершения программа подскажет, где лежит готовый Excel-файл."
    )

    instruction_label = tk.Label(
        root, text=instruction_text, font=("Arial", 12), justify="left", anchor="w"
    )
    instruction_label.pack(fill="x", padx=20)

    cafe_frame = tk.Frame(root)
    cafe_frame.pack(fill="x", padx=20, pady=(10, 10))

    cafe_label = tk.Label(cafe_frame, text="Выберите кафе:", font=("Arial", 12, "bold"))
    cafe_label.pack(side="left")

    selected_cafe = tk.StringVar(value=CAFE_OPTIONS[0])

    cafe_combobox = ttk.Combobox(
        cafe_frame,
        textvariable=selected_cafe,
        values=CAFE_OPTIONS,
        state="readonly",
        font=("Arial", 12),
        width=35,
    )
    cafe_combobox.pack(side="left", padx=(10, 0))

    input_label = tk.Label(
        root,
        text="Вставьте скопированные из Telegram отзывы сюда:",
        font=("Arial", 13, "bold"),
        anchor="w",
    )
    input_label.pack(fill="x", padx=20, pady=(10, 5))

    input_text = scrolledtext.ScrolledText(
        root, wrap=tk.WORD, font=("Arial", 12), height=12
    )
    input_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    log_label = tk.Label(
        root,
        text="Ход выполнения и сообщения программы:",
        font=("Arial", 12, "bold"),
        anchor="w",
    )
    log_label.pack(fill="x", padx=20)

    log_text = scrolledtext.ScrolledText(
        root, wrap=tk.WORD, font=("Consolas", 11), height=8, state="disabled"
    )
    log_text.pack(fill="x", expand=False, padx=20, pady=(5, 10))

    button_frame = tk.Frame(root)
    button_frame.pack(fill="x", padx=20, pady=(0, 20))

    def log(message):
        log_text.configure(state="normal")
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)
        log_text.configure(state="disabled")
        root.update_idletasks()

    def set_buttons_state(state):
        run_button.config(state=state)
        open_folder_button.config(state=state)
        clear_button.config(state=state)
        cafe_combobox.config(state="disabled" if state == "disabled" else "readonly")

    def clear_input():
        input_text.delete("1.0", tk.END)

    def on_run():
        raw_data = input_text.get("1.0", tk.END).strip()
        cafe_name = selected_cafe.get().strip()

        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        log_text.configure(state="disabled")

        if not cafe_name:
            messagebox.showwarning(
                "Не выбрано кафе", "Пожалуйста, выберите кафе из списка перед запуском."
            )
            return

        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Вы выбрали кафе:\n\n{cafe_name}\n\n"
            "Продолжить обработку отзывов для этого кафе?",
        )
        if not confirm:
            return

        if not raw_data:
            messagebox.showwarning(
                "Нет данных",
                "Пожалуйста, вставьте текст отзывов в поле ввода перед запуском.",
            )
            return

        try:
            set_buttons_state("disabled")

            parse_reviews_module.CURRENT_CAFE = cafe_name

            log(f"Выбрано кафе: {cafe_name}")
            log("Сохраняем вставленный текст в raw_reviews.txt...")
            save_input_text(raw_data)
            log(f"Файл входных данных сохранён:\n{INPUT_FILE}")
            log("")

            success = run_pipeline(log)

            if success:
                messagebox.showinfo(
                    "Готово",
                    "Обработка завершена успешно.\n\n"
                    f"Кафе: {cafe_name}\n"
                    f"Результат лежит в папке:\n{OUTPUT_DIR}",
                )
            else:
                messagebox.showerror(
                    "Ошибка",
                    "Обработка завершилась с ошибкой.\n"
                    "Подробности смотрите в поле лога.",
                )

        except Exception:
            error_details = traceback.format_exc()
            log("Произошла критическая ошибка:")
            log(error_details)
            messagebox.showerror(
                "Критическая ошибка",
                "Во время выполнения произошла ошибка.\n"
                "Подробности смотрите в поле лога.",
            )
        finally:
            set_buttons_state("normal")

    run_button = tk.Button(
        button_frame,
        text="Запустить обработку",
        font=("Arial", 13, "bold"),
        height=2,
        command=on_run,
    )
    run_button.pack(side="left", padx=(0, 10))

    clear_button = tk.Button(
        button_frame,
        text="Очистить поле",
        font=("Arial", 12),
        height=2,
        command=clear_input,
    )
    clear_button.pack(side="left", padx=(0, 10))

    open_folder_button = tk.Button(
        button_frame,
        text="Открыть папку с результатом",
        font=("Arial", 12),
        height=2,
        command=open_output_folder,
    )
    open_folder_button.pack(side="left")

    root.mainloop()


if __name__ == "__main__":
    main()
