# SkillQA Pro — архитектура (v0.1.0)

Цель: однозначные спецификации интерфейсов для разработки без уточнений. Документ — русский, идентификаторы кода — английские.

---

## 1. Структура проекта

```
/root/skillqa/
├── skillqa.py            # точка входа: CLI (argparse), оркестратор, отчёты, лицензия, selftest
├── modules/
│   ├── __init__.py       # реестр MODULES: имя → класс (единственное место регистрации)
│   ├── static.py         # класс StaticScan
│   ├── sandbox.py        # класс Sandbox (инфраструктура) + SandboxRun (модуль проверки)
│   ├── log.py            # класс LogAudit
│   ├── novelty.py        # класс NoveltyCheck
│   ├── load.py           # класс LoadTest
│   ├── parallel.py       # класс ParallelTest
│   └── compat.py         # класс CompatCheck
├── fixtures/             # эталонные скиллы для selftest (агент-тестировщик, НЕ трогать)
│   ├── bad_skill/        # сломанный скилл + EXPECTED_BUGS.json
│   └── good_skill/       # чистый эталонный скилл
├── qa_reports/           # генерируется: ./qa_reports/<skill_name>/<дата>.(md|json)
└── README.md, LICENSE    # позже (документатор/упаковщик)
```

Правила:
- Общий код живёт только в `skillqa.py`; модули импортируют его (`modules/__init__.py` добавляет корень в `sys.path`).
- `modules/sandbox.py` — двойная роль: класс `Sandbox` (инфраструктура для всех модулей через `ctx.sandbox`) + класс-модуль `SandboxRun`.
- Реестр: `MODULES = {"static": StaticScan, "sandbox": SandboxRun, "log": LogAudit, "novelty": NoveltyCheck, "load": LoadTest, "parallel": ParallelTest, "compat": CompatCheck}` — порядок словаря = порядок выполнения. Новый модуль = файл + строка в реестре.

---

## 2. Единый интерфейс модуля

Класс с атрибутами класса и одним методом:

| Элемент | Тип | Описание |
|---|---|---|
| `name` | str | Ключ модуля = имя файла = ключ в `MODULES` |
| `title` | dict[str,str] | Название: `{"ru": "Статический анализ", "en": "Static scan"}` |
| `run(ctx)` | Result | Выполняет проверки, возвращает результат |

Контракт `Result` (dict, сериализуется в JSON как есть):

```json
{
  "module": "static", "status": "pass",
  "checks": [
    {"name": "skilmd_exists", "status": "pass", "detail": "SKILL.md найден, 1.2 КБ"},
    {"name": "no_magic_paths", "status": "fail", "detail": "/root/secret.txt, строка 12"}
  ],
  "details": "Сводка: 7 проверок, 1 fail", "duration_ms": 312
}
```

Правила:
- `status` модуля: `pass` — все checks pass; `warn` — есть warn, нет fail; `fail` — есть fail.
- `checks[].status` — только `pass|warn|fail`; `detail` — локализованная строка ≤ 300 символов; `details` — свободная сводка (таблицы статистики), локализуется.
- `duration_ms` ставит оркестратор (замер вокруг `run`).
- Исключение в `run(ctx)` оркестратор превращает в fail-Result с check `{name:"module_crash", status:"fail", detail:"<тип>: <сообщение>"}`.
- Модуль всегда возвращает Result, даже если «нечего проверять» (тогда warn).
- Модули из `ctx.skip` не запускаются и не входят в отчёт и подсчёт балла.

---

## 3. Контекст `ctx`

Создаётся оркестратором один раз на прогон, передаётся в каждый `run(ctx)`:

| Поле | Тип | Описание |
|---|---|---|
| `skill_path` | Path | Абсолютный путь к папке скилла |
| `skill_name` | str | `name` из frontmatter, иначе basename папки; lowercase, `[^a-z0-9_-]`→`_` |
| `lang` | str | `"ru"`/`"en"` (из `--lang`, дефолт `ru`) |
| `timeout` | int | Лимит одного запуска скрипта, сек (дефолт 15, `--timeout`) |
| `load_n` | int | Число прогонов load-теста (дефолт 20, `--load`) |
| `skip` | set[str] | Пропущенные модули (`--skip` + `.qaignore`) |
| `parallel` | bool | Включён parallel-модуль (`--parallel`) |
| `parallel_n` | int | Число экземпляров (дефолт 5, clamp 5–10) |
| `edition` | str | `"demo"`/`"pro"` (раздел 7) |
| `sandbox` | Sandbox | Экземпляр песочницы, один на прогон |
| `tmp_root` | Path | Корень временной папки (`sandbox.tmp_root`) |
| `run_outputs` | list[ExecResult] | Буфер всех запусков скриптов (для log-модуля) |
| `log` | callable | `log(msg, level)` — консольный вывод с учётом `--lang` |

Модули НЕ читают argv и не создают temp-каталоги вне `ctx.sandbox`.

---

## 4. Песочница (Sandbox)

Класс `Sandbox` в `modules/sandbox.py`. Оркестратор создаёт `Sandbox(lang, timeout)`: `tmp_root = tempfile.mkdtemp(prefix="skillqa_")`, копирует скилл в `tmp_root/skill` (скрипты исполняются из копии — оригинал недоступен на запись); по завершении удаляет только `tmp_root` (единственное разрешённое `rmtree`, путь проверяется на префикс `skillqa_`).

```
sandbox.run_script(script: Path, args: list[str] = [], env_extra: dict = {},
                   cwd: Path | None = None, timeout: int | None = None) -> ExecResult
```

`ExecResult` = `{exit_code: int, stdout: str, stderr: str, timed_out: bool, duration_ms: int, rss_kb: int|None}` (`rss_kb` — пиковый RSS: разница `resource.getrusage(RUSAGE_CHILDREN)` до/после; при наличии `/usr/bin/time -v` — из него).

Жёсткие правила исполнения:
1. **cwd** — всегда подпапка `tmp_root/run_<n>` (для parallel — своя на экземпляр).
2. **Очищенное окружение**: `PATH=/usr/bin:/bin`, `HOME=<tmp_root>/home`, `TMPDIR=<tmp_root>/tmp`, `SHELL=/bin/sh`, `LANG=C.UTF-8`; прокси удаляются, `NO_PROXY=*`.
3. **Фейковые токены** (всегда): `OPENAI_API_KEY=sk-fake-000...`, `ANTHROPIC_API_KEY=sk-ant-fake...`, `OPENCLAW_API_KEY=fake-openclaw-0000`, `GITHUB_TOKEN=ghp_fake...`, `AWS_ACCESS_KEY_ID=AKIAFAKE...`, `AWS_SECRET_ACCESS_KEY=fake0000`, `TELEGRAM_BOT_TOKEN=0000000000:fake`, `HF_TOKEN=hf_fake...`, `DATABASE_URL=sqlite:///:memory:`. Реальная переменная с именем, содержащим `TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|AUTH`, удаляется (заменяется фейком из списка).
4. **Без сети**: при root и наличии `unshare` — запуск через `unshare -n`; иначе env-блокировка п.2 + warn. Модули HTTP не делают.
5. **Таймаут kill**: запуск всегда через `timeout --kill-after=2 --signal=KILL <t>`; `timed_out=True` при exit 137.
6. **Интерпретатор** по расширению: `.py`→`python3`, `.sh`→`bash`, `.js`→`node` (нет node — warn); без расширения, но с shebang — `bash`.
7. Оригинал скилла — только на чтение; исполняется копия из `tmp_root/skill`. Ошибка копирования → fail.

### 4.2. Запрещено

Реальные секреты (п.3; дублируется модулем log), сеть (п.4), запись в оригинал скилла и реальный `~` (HOME подменён, cwd внутри tmp). `rm -rf` физически невозможен вне tmp: изоляция достигается окружением и путями, фильтрация команд не нужна.

---

## 5. Семь модулей: проверки

Имена checks — английские (стабильные ключи JSON), `detail` — локализуемый. Указаны условия статусов.

### 5.1. static.py — StaticScan
1. `skilmd_exists` — SKILL.md есть и читается, размер > 200 байт: иначе fail.
2. `frontmatter_valid` — блок между `---` в начале — валидный YAML: иначе fail.
3. `frontmatter_fields` — обязательные `name`, `description`, `version`; отсутствие `tools`/`allowed-tools` — warn; нет обязательных — fail.
4. `referenced_paths_exist` — все пути/файлы, упомянутые в SKILL.md, существуют: каждый битый — fail.
5. `no_empty_broken_files` — файлы скилла (кроме SKILL.md) размером 0 или нечитаемые — fail; бинарники > 1 МБ в корне — warn.
6. `no_magic_paths` — абсолютные пути (`/home/`, `/root/`, `C:\`, `/Users/`) — fail; `~/` — warn.
7. `reasonable_sizes` — файл > 5 МБ — warn.
8. `version_consistent` — `version` не semver (`\d+\.\d+\.\d+`) — warn; расхождение с упоминаниями в SKILL.md — warn.

### 5.2. sandbox.py — SandboxRun
Обнаружение: `*.py|*.sh|*.js` в корне скилла (рекурсивно — только если в корне один файл). Нет скриптов → модуль `warn`, details «исполняемых скриптов не найдено». Для каждого скрипта S:
1. `run_<basename>` — пустой argv, fake-env, cwd=tmp: exit 0 и пустой stderr → pass; exit 0 со stderr → warn; exit ≠ 0 или traceback → fail.
2. `help_<basename>` — `S --help`: exit 0 → pass; exit ≠ 0, но в выводе `usage|help|использование` → warn; краш/traceback/hang → fail.
3. `noargs_<basename>` — `S` без аргументов: exit ≠ 0 с понятным сообщением (usage/error/«требуется») → pass; exit 0 → warn («молчаливый успех»); traceback/hang → fail.
4. `sandbox_isolated` — ни один запуск не завис и не писал вне tmp: pass/warn по факту.
`details` — таблица скрипт × (exit, время, timed_out).

### 5.3. log.py — LogAudit
Сканирует: выводы всех запусков (`ctx.run_outputs`), текстовые файлы скилла (≤ 1 МБ), `*.log`-файлы.
1. `logging_present` — скилл пишет логи (logging/logger/print-to-file/`.log`-файлы): нет — pass «логирование не обнаружено».
2. `log_rotation` — append-логирование без ротации (`a+`, `open(...,"a")`, нет `RotatingFileHandler`) → warn.
3. `error_quality` — traceback с `File "...", line N` → pass; «голая» ошибка без файла:строки → warn; traceback без файла:строки → fail.
4. `secret_leak` — regex по всем текстам: `Bearer\s+[A-Za-z0-9._\-]{16,}`, `sk-[A-Za-z0-9]{16,}`, `(token|api[_-]?key|password|secret|auth)\s*[=:]\s*\S{12,}`, `AKIA[0-9A-Z]{16}`, `-----BEGIN ... PRIVATE KEY`, hex ≥ 32 симв. подряд, base64 ≥ 40 симв. в контексте присваивания. Совпадение → fail (до 5 деталей). Точное совпадение со значением фейкового токена игнорируется.
5. `log_growth` — файловый лог без ротации/лимита размера → warn.

### 5.4. novelty.py — NoveltyCheck
Библиотека: `~/.openclaw/skills`, `~/.openclaw/workspace/skills`, `$OPENCLAW_SKILLS_DIR`, кэш ClawHub `~/.openclaw/clawhub` (если есть). Скилл = папка с SKILL.md.
1. `name_collision` — в библиотеке есть SKILL.md с тем же `name` → fail; совпадение имени папки иначе → warn.
2. `description_overlap` — difflib ratio по description: ≥ 0.85 → fail; 0.6–0.85 → warn.
3. `description_not_empty` — пусто/короче 20 симв./шаблон («Описание», «A skill that...», «TODO») → fail.
4. `has_examples` — секция примеров (`## Examples`/`## Примеры`/`Usage`) или пример в ```-блоке → pass; нет → warn.
5. `library_reachable` — библиотека не найдена вовсе → warn, checks 1–2 пропускаются.
Вердикт в `details`: «добавляет ценность» / «дублирует скилл N».

### 5.5. load.py — LoadTest
Главный скрипт: (1) путь из SKILL.md с маркером `main`/`run`; (2) иначе первый `*.py` в корне; (3) иначе первый исполняемый файл. Нет скрипта → модуль warn.
1. `runs_completed` — `ctx.load_n` прогонов главного скрипта в песочнице: все без timeout → pass; hang → fail.
2. `timing_stats` — min/avg/max/median и `rss_kb` каждого прогона в `details`.
3. `no_degradation` — `avg(t[последние 5]) > 1.5 × avg(t[первые 5])` → fail; `max > 3 × median` → warn; иначе pass.
4. `no_memory_leak` — RSS последних 5 в среднем > 120% первых 5 → fail; метрика недоступна → warn; иначе pass.
5. `hang_detected` — любой прогон `timed_out` → fail.

### 5.6. parallel.py — ParallelTest
Только при `--parallel`, иначе пропускается оркестратором. Требует главного скрипта (выбор как 5.5) — нет → warn.
1. `all_finished` — `parallel_n` одновременных запусков (Popen, контрольный таймаут `timeout × 2`): все завершились → pass; любой не завершился → fail (взаимоблокировка/зависание).
2. `exit_codes_ok` — все exit 0 → pass; часть ≠ 0 → warn; все ≠ 0 → fail.
3. `unique_tmp_files` — каждый экземпляр в своей `tmp_root/par_<i>` создал файл (или выводы различаются) → pass; никто не создаёт → warn «нет уникальных temp-файлов»; несколько пишут в один путь → fail.
4. `no_conflicts` — в stderr нет `FileExistsError|PermissionError|locked|already exists|resource busy` → pass; есть → fail.

### 5.7. compat.py — CompatCheck
1. `python_required` — shebang и фичи кода: `match`/`case` → 3.10+, `|` в type hints → 3.10+, walrus `:=` → 3.8+, f-string `=` → 3.8+: details «требуется Python ≥ X»; неоднозначно → warn.
2. `deps_installable` — `requirements.txt`/`pyproject.toml` парсятся → pass; битый синтаксис → fail. Сторонние импорты (ast) проверяются `python3 -c "import X"` в песочнице: отсутствующие → warn (окружение OpenClaw может отличаться), перечень в details.
3. `runs_on_installed_pythons` — для каждого найденного `python3.10/3.11/3.12` (shutil.which) запуск главного скрипта с `--help` под этой версией: exit 0 → pass; краш → fail с указанием версии. Доступна одна версия → warn «протестировано только на X».
4. `version_features_noted` — версионозависимые фичи из п.1 в details (всегда pass).

---

## 6. Оркестратор и CLI

### 6.1. Команды (argparse, prog=`skillqa`)

```
python3 skillqa.py test <путь> [опции]
python3 skillqa.py selftest [--lang ru|en] [--timeout S] [--load N]
python3 skillqa.py license --install <файл> | --status | --machine-id
python3 skillqa.py --version | -h
```

Опции `test`:
- `--lang {ru,en}` — язык сообщений и отчёта (дефолт `ru`).
- `--demo` / `--pro` — принудительный режим; без флага: `pro` при валидной лицензии, иначе `demo`. `--pro` без лицензии → ошибка, exit 3.
- `--skip m1,m2,...` — пропуск модулей; объединяется с `.qaignore`.
- `--load N` — число прогонов load (дефолт 20).
- `--parallel [N]` — включить parallel-модуль, N экземпляров (дефолт 5, clamp 5–10).
- `--timeout S` — лимит запуска скрипта, сек (дефолт 15).

`.qaignore` (в корне скилла): имя модуля на строку, `#` — комментарии, пустые строки игнорируются; битая строка → warn в отчёте.

Exit codes: `0` — нет fail; `1` — есть fail; `2` — ошибка использования (argparse); `3` — лицензия (нет/невалидна при `--pro`).

### 6.2. Порядок прогона `test`

1. Парсинг argv, определение `edition` (раздел 7).
2. Валидация `<путь>`: существует и каталог — иначе exit 2.
3. Создание `Sandbox` (копия скилла, fake-env).
4. Чтение `.qaignore` → `ctx.skip` (+ `--skip`).
5. Для каждого модуля из `MODULES` (кроме пропущенных и parallel без флага): `run(ctx)` с замером; консоль: `[✓/!/✗] модуль — статус (N мс)`, цвет.
6. Подсчёт балла и вердикта (6.3), генерация отчётов (6.4), консольная сводка.
7. Очистка `tmp_root`.

Бюджет: static + sandbox на реальном скилле < 60 сек (DoD). Общий лимит 300 сек — при превышении оркестратор прерывает, незавершённые модули помечает fail, отчёт пишет.

### 6.3. Вердикт

Очки: `pass`=2, `warn`=1, `fail`=0. `score_pct = сумма / (2 × число_выполненных_модулей)`. Пропущенные не считаются. Буква: **A** — `fail_count == 0` и `score_pct ≥ 0.85`; **B** — `fail_count ≤ 1` и `score_pct ≥ 0.65`; **C** — `score_pct ≥ 0.45`; иначе **D**. Fail в `sandbox` или `log` опускает потолок до **B** (краши/утечки секретов несовместимы с A).

### 6.4. Отчёты

Всегда в `./qa_reports/<skill_name>/` (папка создаётся):
- `<YYYY-MM-DD>_<HHMMSS>.md` — человекочитаемый (формат — раздел 8);
- `<YYYY-MM-DD>_<HHMMSS>.json` — машиночитаемый, только в pro.

JSON-схема:
```json
{
  "tool": "skillqa", "version": "0.1.0", "edition": "pro",
  "skill_name": "...", "skill_path": "...", "grade": "A",
  "score_pct": 0.93, "fail_count": 0, "date": "2026-08-19T12:00:00Z",
  "lang": "ru", "skipped": [], "duration_ms": 12345,
  "modules": [{"module": "...", "status": "...", "checks": [], "details": "...", "duration_ms": 0}]
}
```

Demo-режим: запускается только `static`; отчёт-тизер (Markdown, суффикс `_demo`): результат static + промо-блок (перечень 7 модулей, сертификат, JSON для CI, реквизиты из 7.4). JSON в demo не пишется.

---

## 7. Лицензирование (образец ViBo)

### 7.1. Machine-id
`sha256(<первый из: /etc/machine-id, /var/lib/dbus/machine-id, hostname>)` → первые 16 hex; команда `license --machine-id`.

### 7.2. Файл лицензии
Путь: `~/.config/skillqa/license.key` (создаётся `license --install`). Одна JSON-строка:
```json
{"machine_id": "a1b2...", "edition": "pro", "expires": "2027-12-31", "sig": "<hex hmac-sha256>"}
```
`sig` = HMAC-SHA256(встроенный_секрет, канонический JSON полей `machine_id|edition|expires`) в hex. Секрет — константа в `skillqa.py` (позже допустима защита .so/обфускация без изменения архитектуры).

### 7.3. Проверка (при каждом запуске)
Последовательно: файл существует и парсится; `hmac.compare_digest` recomputed sig == sig; `machine_id` файла == текущий; `expires >= сегодня`. Любое нарушение → статус `no_license / bad_signature / wrong_machine / expired` и режим demo (+ warning). `--pro` при статусе ≠ `valid` → exit 3 с сообщением и подсказкой `license --install`. `--status` печатает статус, edition, expires, machine-id.

### 7.4. Конфиг-плейсхолдер оплаты (ViBo «Модель А»)
Константа в `skillqa.py`: `PAYMENT = {"usdt_trc20": "T...ПОДСТАВИТЬ_ПЕРЕД_РЕЛИЗОМ", "telegram_stars": "@...ПОДСТАВИТЬ"}` — используется только в тизере demo и README. Сетевой проверки оплаты в v0.1.0 нет.

---

## 8. Отчёт-сертификат (Markdown, pro)

Структура `qa_reports/<skill>/<дата>.md`:
1. Шапка: ASCII-логотип `SKILLQA PRO`, строка «СЕРТИФИЦИРОВАНО SKILLQA PRO», имя скилла, дата, версия тула.
2. Вердикт крупно: `Оценка: A (93/100)`.
3. Таблица модулей: модуль | статус | время | число checks (✓/!/✗).
4. Секция по каждому модулю: checks (иконка + name + detail), `details` цитатой.
5. Сводка: пропущенные модули, общее время, окружение (Python, OS).
6. Подпись: «Сертифицировано SkillQA Pro v0.1.0» + machine-id владельца + срок лицензии. Этот файл автор показывает покупателям.
7. Demo-тизер: вместо 3–6 — результат static + промо-блок.

---

## 9. Selftest

`selftest` — 4 фазы; любая fail-фаза → exit 1; вывод — чек-лист `[OK/FAIL]`.

1. **Целостность**: `skillqa.py` и `modules/*.py` прогоняются через собственные static + sandbox (`python3 skillqa.py test . --lang en --skip parallel,novelty,load` как subprocess, таймаут 120 с). Краш — fail.
2. **Ловля багов bad_skill**: полный прогон `test fixtures/bad_skill` (все модули). Контракт: `fixtures/bad_skill/EXPECTED_BUGS.json` = массив `[{bug_id, module, check, hint}]` (минимум 5 багов: крашащийся скрипт, утечка токена в логе, битый путь в SKILL.md, магический путь, висящий скрипт). Для каждого `bug_id` соответствующий check в отчёте должен быть `fail`; пропущенный → fail фазы с перечнем.
3. **Чистота good_skill**: `test fixtures/good_skill` — ни одного fail (warn допустимы).
4. **Стабильность**: 3 прогона good_skill; нормализованные JSON (без `duration_ms` и дат) идентичны; расхождение → fail.

Защита от рекурсии: selftest не вызывает selftest; fixtures не содержат и не вызывают skillqa.

---

## 10. i18n

Словарь `I18N = {"ru": {...}, "en": {...}}` в `skillqa.py`: ключи `module.<name>.title`, `check.<name>` (заголовок), `check.<name>.desc` (шаблон detail с `{}`-плейсхолдерами), `cli.*`. Недостающий ключ → fallback на английский + одноразовый warn. Статусы, имена checks и модулей — всегда английские (контракт JSON).

---

## 11. Ограничения v0.1.0

- Python 3.10+; мультиверсионное тестирование — только в compat (обнаружение установленных интерпретаторов).
- Novelty по ClawHub — только оффлайн-кэш; сетевой API не вызывается.
- Hang-скрипты выявляются таймаутом (дефолт 15 с) — selftest держит `--timeout` явным. Ни один модуль не пишет в оригинал скилла.
