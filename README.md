# Cafe Review Parser

Desktop utility for semi-automatic processing of guest reviews collected inside a cafe network.

The application helps managers and directors transform raw review text into a structured Excel report with:
- extracted review entries,
- detected dishes,
- estimated sentiment,
- review tagging,
- issue classification,
- summary sheets for operational analysis.

## Project goal

This tool was created to reduce manual work when processing guest feedback from internal communication channels.

Instead of manually copying reviews into Excel and formatting each entry by hand, the user can:
1. paste raw review text into the application window,
2. select the cafe branch,
3. run automated parsing,
4. receive a prefilled Excel file for validation and further analysis.

## Key features

- Desktop GUI built with `tkinter`
- Parsing raw text copied from Telegram desktop
- Support for an alternative email-export text format from mobile devices
- Automatic assignment of cafe branch
- Review filtering and noise detection
- Dish extraction using internal aliases and domain-specific rules
- Rule-based sentiment detection
- Review type / tag / priority estimation
- Export to structured Excel and CSV files
- Summary tables for operational reporting

## Use case

The tool is designed for a specific cafe chain and contains:
- branch-specific naming,
- internal menu aliases,
- domain-specific parsing rules,
- heuristics tuned for real review workflows.

This is an early production-oriented version intended for internal use and iterative improvement based on user feedback.

## Tech stack

- Python 3
- tkinter
- openpyxl

## How it works

1. User launches the app
2. Selects a cafe from a fixed list
3. Pastes raw reviews into the input field
4. Application saves source text to `raw_reviews.txt`
5. Parsing pipeline processes reviews
6. Structured Excel report is generated
7. User performs final manual validation in spreadsheet

## Input formats

The parser supports two input scenarios:

### 1. Telegram Desktop
Reviews are selected in Telegram desktop client and copied as plain text.

### 2. Mobile fallback via email
If Telegram desktop is unavailable, selected messages can be shared from mobile device via email.  
The user then copies the message text from email and pastes it into the app.

## Output

The application generates results in the `ГОТОВЫЙ_РЕЗУЛЬТАТ` folder:
- intermediate CSV files,
- final Excel workbook (`ГОТОВАЯ_ТАБЛИЦА`).

## Important notes

- Parsing is not 100 percent accurate
- The tool is designed to accelerate formatting, filtering and pre-classification
- Final validation is performed manually by the responsible manager/director
- For best compatibility, the resulting Excel file is recommended to be opened in Google Sheets
- Some dropdown validation controls may need to be re-enabled manually in Google Sheets

## Screenshots

Add screenshots here:

- Main application window
- Cafe selection
- Input example
- Result folder
- Google Sheets validation dropdown example

## Repository structure
```text
run_app.py                      # GUI entry point
scripts/                        # parsing and export logic
ШАБЛОН_НЕ_ТРОГАТЬ/              # Excel template
ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ/  # raw input text file
ГОТОВЫЙ_РЕЗУЛЬТАТ/              # generated files
docs/                           # documentation and screenshots
```
---

# [RU]

# Парсер отзывов о кафе

Настольная утилита для полуавтоматической обработки отзывов посетителей, собранных в сети кафе.

Приложение помогает менеджерам и директорам преобразовывать исходный текст отзывов в структурированный отчет Excel, содержащий:
- извлеченные записи отзывов,
- обнаруженные блюда,
- оценку тональности,
- теги отзывов,
- классификацию проблем,
- сводные таблицы для оперативного анализа.

## Цель проекта

Этот инструмент создан для сокращения ручной работы при обработке отзывов посетителей из внутренних каналов связи.

Вместо того чтобы вручную копировать отзывы в Excel и форматировать каждую запись вручную, пользователь может:
1. вставить исходный текст отзыва в окно приложения,
2. выбрать филиал кафе,
3. запустить автоматический парсинг,
4. получить предварительно заполненный файл Excel для проверки и дальнейшего анализа.

## Ключевые особенности

- Графический интерфейс пользователя для настольных компьютеров, созданный с помощью `tkinter`
- Анализ необработанного текста, скопированного из Telegram для настольных компьютеров
- Поддержка альтернативного формата экспорта текста по электронной почте с мобильных устройств
- Автоматическое назначение филиала кафе
- Фильтрация отзывов и обнаружение шума
- Извлечение блюд с использованием внутренних псевдонимов и правил, специфичных для предметной области
- Определение тональности на основе правил
- Оценка типа/тега/приоритета отзыва
- Экспорт в структурированные файлы Excel и CSV
- Сводные таблицы для оперативной отчетности

## Пример использования

Инструмент разработан для конкретной сети кафе и содержит:
- именование, специфичное для филиала,
- внутренние псевдонимы меню,
- правила анализа, специфичные для предметной области,
- эвристики, настроенные для реальных рабочих процессов обработки отзывов.

Это ранняя версия, ориентированная на использование в производственной среде, предназначенная для внутреннего использования и итеративного улучшения на основе отзывов пользователей.

## Технологический стек

- Python 3
- tkinter
- openpyxl

## Как это работает

1. Пользователь запускает приложение
2. Выбирает кафе из фиксированного списка
3. Вставляет необработанные отзывы в поле ввода
4. Приложение сохраняет исходный текст в файл `raw_reviews.txt`
5. Конвейер парсинга обрабатывает отзывы
6. Генерируется структурированный отчет Excel
7. Пользователь выполняет окончательную ручную проверку в электронной таблице

## Форматы ввода

Парсер поддерживает два сценария ввода:

### 1. Telegram Desktop
Отзывы выбираются в настольном клиенте Telegram и копируются как обычный текст.

### 2. Мобильный резервный вариант через электронную почту
Если настольный Telegram недоступен, выбранные сообщения можно отправить с мобильного устройства по электронной почте.

Затем пользователь копирует текст сообщения из электронной почты и вставляет его в приложение.

## Выход

Приложение формирует результаты в папке «ГОТОВЫЙ_РЕЗУЛЬТАТ»:
- промежуточные файлы CSV,
- итоговая книга Excel («ГОТОВАЯ_ТАБЛИЦА»).

## Важные примечания

- Парсинг не на 100% точен
- Инструмент предназначен для ускорения форматирования, фильтрации и предварительной классификации
- Окончательная проверка выполняется вручную ответственным менеджером/директором
- Для наилучшей совместимости рекомендуется открывать полученный файл Excel в Google Sheets
- Некоторые элементы управления проверкой выпадающих списков могут потребовать повторного включения вручную в Google Sheets

## Скриншоты

Добавьте скриншоты здесь:

- Главное окно приложения
- Выбор кафе
- Пример ввода
- Папка с результатами
- Пример выпадающего списка проверки в Google Sheets

## Структура репозитория
```text
run_app.py # Точка входа в графический интерфейс пользователя
scripts/ # Логика парсинга и экспорта
ШАБЛОН_НЕ_ТРОГАТЬ/ # Шаблон Excel
ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ/ # Исходный текстовый файл ввода
ГОТОВЫЙ_РЕЗУЛЬТАТ/ # Сгенерированные файлы
docs/ # Документация и скриншоты
```
