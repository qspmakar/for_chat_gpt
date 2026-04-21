# Houdini ⇄ Maya Alembic Bridge (v1)

Простой двусторонний мост для обмена Alembic (`.abc`) между Houdini и Maya «по кнопке».

## Цели v1

- Экспорт из **Houdini** выбранной `SOP` или `OBJ` ноды в Alembic.
- Импорт этого Alembic в **Maya** одной кнопкой.
- Экспорт из **Maya** выделенных объектов в Alembic.
- Импорт этого Alembic в **Houdini** одной кнопкой.
- Сохранение пользовательских атрибутов (насколько позволяет Alembic pipeline).
- Минимум настроек: общий `Bridge Folder` + префикс шота/сцены.

## Архитектура v1

Обмен делается через общую папку, доступную обоим DCC:

- Пример: `//server/projects/bridge_exchange`
- Каждая отправка создает:
  - `*.abc` — Alembic файл
  - `*.json` — sidecar метаданные (направление, время, объект, атрибуты, path-map)

### Именование

`{scene}_{sourceDcc}_{timestamp}.abc`

Пример:
`ep010_sh030_houdini_20260421_143012.abc`

## Тонкость с `path` атрибутом

### Что важно

В Houdini часто есть примитивный строковый атрибут `path`, который задает иерархию при экспорте.
Если его не нормализовать, в Maya иерархия может «распасться» или получить неожиданные имена.

### Правила v1

1. Перед экспортом из Houdini гарантируем, что `path`:
   - строковый
   - примитивный
   - начинается с `/`
   - не содержит пробелов и спецсимволов (заменяем на `_`)
2. При экспорте из Maya сохраняем DAG paths в `sidecar json` (`dag_paths`).
3. При импорте в Houdini создаем/обновляем `path` (если нужно) на основе `dag_paths`.

Это закрывает основной риск несовпадения иерархий между DCC.

## Атрибуты

### Houdini -> Maya

- Экспортируем user attrs через Alembic ROP параметры:
  - `build_from_path` с `path`
  - `prim_to_detail` по необходимости (опционально)
- Рекомендация v1: держать атрибуты в примитивах/вершинах и использовать простые типы.

### Maya -> Houdini

- При экспорте используем `AbcExport -attr` для whitelist атрибутов.
- Список whitelisted attrs хранится в конфиге.

## Файлы v1

- `houdini_bridge.py` — shelf tool / python panel callbacks для Houdini.
- `maya_bridge.py` — shelf buttons для Maya.
- `bridge_config_example.json` — пример конфига.

## Быстрый старт

1. Скопировать скрипты в пайплайн-репозиторий.
2. Создать `bridge_config.json` по образцу.
3. В Houdini повесить:
   - `export_selected_to_maya()`
   - `import_latest_from_maya()`
4. В Maya повесить:
   - `export_selected_to_houdini()`
   - `import_latest_from_houdini()`

## Куда именно класть файлы (практически)

Ниже — рабочий вариант для v1 без сложного деплоя.

### 1) Общая сетевая папка (для `.abc` + `.json`)

- Создай папку, доступную и Houdini, и Maya:
  - Windows пример: `\\\\server\\projects\\bridge_exchange`
  - Linux пример: `/mnt/projects/bridge_exchange`
- Эту папку укажи в `bridge_config.json` как `bridge_folder`.

### 2) Куда класть Python-скрипты

Рекомендуемый вариант для v1 — отдельная папка tools в пайплайне, например:

- `//server/pipeline/tools/bridge_v1/houdini_bridge.py`
- `//server/pipeline/tools/bridge_v1/maya_bridge.py`
- `//server/pipeline/tools/bridge_v1/bridge_config.json`

Важно: обе DCC должны видеть один и тот же путь к `bridge_config.json`.

### 3) Houdini: куда подключать

Локально у художника:

- `~/houdini20.5/scripts/python/` (или версия Houdini, которую используешь)
- либо просто добавить путь `//server/pipeline/tools/bridge_v1` в `HOUDINI_PATH`/`PYTHONPATH`.

Shelf Tool (Python) для экспорта в Maya:

```python
import sys
sys.path.append(r"//server/pipeline/tools/bridge_v1")
import houdini_bridge as hb
hb.export_selected_to_maya(r"//server/pipeline/tools/bridge_v1/bridge_config.json")
```

Shelf Tool (Python) для импорта из Maya:

```python
import sys
sys.path.append(r"//server/pipeline/tools/bridge_v1")
import houdini_bridge as hb
hb.import_latest_from_maya(r"//server/pipeline/tools/bridge_v1/bridge_config.json")
```

### 4) Maya: куда подключать

Локально у художника:

- `~/Documents/maya/scripts/` (Windows)
- `~/maya/scripts/` (Linux)
- либо добавить `//server/pipeline/tools/bridge_v1` в `PYTHONPATH`.

Shelf Button (Python) экспорт в Houdini:

```python
import sys
sys.path.append(r"//server/pipeline/tools/bridge_v1")
import maya_bridge as mb
mb.export_selected_to_houdini(r"//server/pipeline/tools/bridge_v1/bridge_config.json")
```

Shelf Button (Python) импорт из Houdini:

```python
import sys
sys.path.append(r"//server/pipeline/tools/bridge_v1")
import maya_bridge as mb
mb.import_latest_from_houdini(r"//server/pipeline/tools/bridge_v1/bridge_config.json")
```

## Ограничения v1

- Нет live-сокетов: только file-based обмен.
- Нет conflict resolution при параллельной работе нескольких артистов.
- Нет UI кроме стандартных message boxes/log.
