# Менеджер задач — REST API на FastAPI + PostgreSQL

![CI](https://github.com/crasavella04/python-lab6/actions/workflows/ci.yml/badge.svg)

Практическая работа №2: REST API на **FastAPI** с хранением данных в **PostgreSQL** через **SQLAlchemy 2.0 (async)**,
валидацией через **Pydantic v2**, миграциями **Alembic** и middleware **Starlette**
(состояние на момент сдачи — тег [`lab6`](https://github.com/crasavella04/python-lab6/tree/lab6)).

Практическая работа №3: автотесты на **pytest** с реальной PostgreSQL, многоэтапный **Dockerfile**,
полный **docker-compose** (приложение + БД + миграции) и CI/CD в **GitHub Actions** с публикацией образа
в GHCR и Docker Hub — см. разделы [Тесты](#тесты), [Docker](#docker), [CI/CD](#cicd).

## Стек

| Компонент | Назначение |
|---|---|
| FastAPI | веб-фреймворк, роутеры, зависимости, Swagger UI |
| SQLAlchemy 2.0 + asyncpg | асинхронный ORM и драйвер PostgreSQL |
| Pydantic v2 + pydantic-settings | схемы запросов/ответов и конфигурация из окружения |
| Alembic | миграции схемы БД |
| PostgreSQL 16 (Docker) | хранилище |
| pytest + pytest-asyncio + httpx | автотесты API |
| ruff | линтер |
| Docker, Docker Compose | контейнеризация |
| GitHub Actions, GHCR, Docker Hub | CI/CD и реестры образов |

## Структура проекта

```
.
├── .github/workflows/
│   └── ci.yml           # CI/CD: lint, test, build
├── app/
│   ├── __init__.py
│   ├── main.py          # создание приложения, middleware, подключение роутеров
│   ├── config.py        # настройки (pydantic-settings), DATABASE_URL
│   ├── db.py            # async-движок, фабрика сессий, Base, get_session
│   ├── models.py        # ORM-модели User и Task (Mapped / mapped_column)
│   ├── schemas.py       # Pydantic-схемы *Create / *Read / *Update
│   └── routers/
│       ├── users.py     # POST /users, GET /users/{id}
│       └── tasks.py     # CRUD /tasks
├── migrations/          # Alembic (шаблон async)
│   └── versions/        # миграция create users and tasks
├── tests/
│   ├── conftest.py      # тестовая БД tasks_test, очистка таблиц, подмена get_session
│   ├── test_users.py
│   ├── test_tasks.py
│   └── test_middleware.py
├── screenshots/         # скриншоты для отчёта
├── alembic.ini
├── Dockerfile           # многоэтапная сборка: builder → test / runtime
├── docker-compose.yml   # db + app (миграции перед стартом) + tests
├── pyproject.toml       # настройки ruff
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt # pytest, pytest-asyncio, httpx, ruff
├── .env.example
└── README.md
```

## Эндпоинты

| Метод | Путь | Описание | Коды ответа |
|---|---|---|---|
| POST | `/users` | создать пользователя | 201, 409 (email занят), 422 |
| GET | `/users/{id}` | получить пользователя | 200, 404 |
| POST | `/tasks` | создать задачу | 201, 404 (нет владельца), 422 |
| GET | `/tasks` | список задач, фильтры `done`, `owner_id`, пагинация `limit` (1–100), `offset` | 200 |
| GET | `/tasks/{id}` | получить задачу | 200, 404 |
| PATCH | `/tasks/{id}` | частично обновить задачу | 200, 404, 422 |
| DELETE | `/tasks/{id}` | удалить задачу | 204, 404 |

Middleware в `app/main.py` добавляет к каждому ответу заголовок `X-Process-Time` и пишет в лог метод, путь, статус и время обработки:

```
2026-10-27 21:48:26,727 INFO app.requests: PATCH /tasks/1 -> 200 (27.64 ms)
2026-10-27 21:48:27,263 INFO app.requests: DELETE /tasks/1 -> 404 (18.62 ms)
```

## Инструкция по запуску

Требуется Python 3.11+, Docker и Docker Compose.

**1. Клонировать репозиторий**

```bash
git clone https://github.com/crasavella04/python-lab6.git
cd python-lab6
```

**2. Создать файл `.env`** из примера (строка подключения в коде не хранится, она читается из `DATABASE_URL`):

```bash
cp .env.example .env
```

> Порт 5432 на машине должен быть свободен (его использует контейнер PostgreSQL).

**3. Запустить PostgreSQL и проверить доступность**

```bash
docker compose up -d db
docker compose exec db psql -U app -d tasks -c "select 1"
```

**4. Создать виртуальное окружение и установить зависимости**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**5. Применить миграции** (таблицы создаются только Alembic, без `create_all`)

```bash
alembic upgrade head
```

Миграция в репозитории уже сгенерирована. Для справки — как она была получена:

```bash
alembic init -t async migrations
alembic revision --autogenerate -m "create users and tasks"
```

**6. Запустить сервис**

```bash
uvicorn app.main:app --reload
```

**7. Открыть Swagger UI:** <http://localhost:8000/docs>

**8. Проверить таблицы в БД**

```bash
docker compose exec db psql -U app -d tasks -c "\dt"
```

Остановить БД: `docker compose down` (с удалением данных: `docker compose down -v`).

## Тесты

Тесты работают с реальной PostgreSQL, но в отдельной БД **`tasks_test`** (создаётся автоматически, если её нет).
Перед каждым тестом все таблицы очищаются (`TRUNCATE ... RESTART IDENTITY`), а зависимость `get_session`
подменяется через `app.dependency_overrides` на сессию тестовой БД.

| Тест | Что проверяет |
|---|---|
| `test_create_user` | создание пользователя → 201 |
| `test_create_user_duplicate_email` | повторный email → 409 |
| `test_create_user_invalid_email` | невалидный email → 422 |
| `test_create_task` | создание задачи → 201 |
| `test_create_task_unknown_owner` | задача с несуществующим владельцем → 404 |
| `test_list_tasks_filter_done_and_pagination` | фильтр `done` и пагинация `limit`/`offset` |
| `test_patch_updates_only_sent_fields` | PATCH меняет только переданные поля |
| `test_delete_then_get_returns_404` | DELETE → 204, затем GET → 404 |
| `test_process_time_header` | наличие заголовка `X-Process-Time` |

### Запуск тестов локально

```bash
docker compose up -d db
pip install -r requirements-dev.txt
python -m pytest -v
ruff check .
```

Адрес тестовой БД по умолчанию — `postgresql+asyncpg://app:app@localhost:5432/tasks_test`,
его можно переопределить переменной окружения `TEST_DATABASE_URL`.

### Запуск тестов через Docker Compose

```bash
docker compose --profile test run --rm --build tests
```

Сервис `tests` собирается из этапа `test` Dockerfile, дожидается готовности `db` и запускает `pytest`.

## Docker

`Dockerfile` использует многоэтапную сборку:

- **builder** — ставит зависимости из `requirements.txt` в виртуальное окружение `/opt/venv`;
- **test** — на основе builder добавляет `requirements-dev.txt` и тесты (используется только сервисом `tests`);
- **runtime** — финальный образ на `python:3.12-slim`: копирует из builder только готовый `/opt/venv`,
  код приложения и миграции и запускается от непривилегированного пользователя `app`.

Запуск всего приложения (БД + миграции + API):

```bash
docker compose up -d --build
```

- `db` объявлен с healthcheck (`pg_isready`);
- `app` стартует только после того, как `db` стала `healthy` (`depends_on: condition: service_healthy`),
  и перед запуском uvicorn выполняет `alembic upgrade head`.

Swagger UI: <http://localhost:8000/docs>. Остановить: `docker compose down`.

## CI/CD

Workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) запускается на каждый `push` и `pull_request`:

| Job | Когда | Что делает |
|---|---|---|
| `lint` | всегда | `ruff check .` |
| `test` | всегда | поднимает service-контейнер `postgres:16` и запускает `pytest` |
| `build` | только `push` в `main` и только после успешных `lint` и `test` (`needs`) | собирает образ (этап `runtime`) и публикует его в GHCR и Docker Hub с тегами `latest` и `sha-<коммит>` |

Для входа в GHCR используется встроенный `GITHUB_TOKEN`, для Docker Hub — секреты репозитория
`DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN`.

### Проверка pipeline (pull request с намеренно сломанным тестом)

В [PR #1](https://github.com/crasavella04/python-lab6/pull/1) тест `test_create_user` был намеренно
сломан (ожидался код 200 вместо 201), затем исправлен, после чего PR был смёржен.

**«Упавший» pipeline** — [run](https://github.com/crasavella04/python-lab6/actions/runs/40730244896):
job `test` упал, `build` пропущен.

![CI failed](screenshots/14_ci_pr_failed.png)

**Успешный pipeline** после исправления теста — [run](https://github.com/crasavella04/python-lab6/actions/runs/40730636044):

![CI success](screenshots/15_ci_pr_fixed.png)

### Опубликованные образы

- **GHCR:** [ghcr.io/crasavella04/python-lab6](https://github.com/crasavella04/python-lab6/pkgs/container/python-lab6)

  ```bash
  docker pull ghcr.io/crasavella04/python-lab6:latest
  ```

- **Docker Hub:** [hub.docker.com/repository/docker/crasavella/python-lab6](https://hub.docker.com/repository/docker/crasavella/python-lab6)

  ```bash
  docker pull crasavella/python-lab6:latest
  ```

## Скриншоты (практическая работа №2)

### Swagger UI — общий вид

![Swagger UI](screenshots/00_swagger_overview.png)

### Пользователи

**POST /users → 201 Created**

![POST /users 201](screenshots/01_post_users_201.png)

**POST /users с занятым email → 409 Conflict**

![POST /users 409](screenshots/02_post_users_409.png)

**GET /users/1 → 200 OK**

![GET /users/1 200](screenshots/03_get_user_200.png)

**GET /users/999 → 404 Not Found**

![GET /users/999 404](screenshots/04_get_user_404.png)

### Задачи

**POST /tasks → 201 Created**

![POST /tasks 201](screenshots/05_post_tasks_201.png)

**POST /tasks с несуществующим владельцем → 404 Not Found**

![POST /tasks 404](screenshots/06_post_tasks_404.png)

**POST /tasks с пустым title → 422 Unprocessable Entity**

![POST /tasks 422](screenshots/07_post_tasks_422.png)

**GET /tasks?done=false&owner_id=1&limit=10&offset=0 → 200 OK** (фильтры и пагинация)

![GET /tasks 200](screenshots/08_get_tasks_filter_200.png)

**GET /tasks/1 → 200 OK**

![GET /tasks/1 200](screenshots/09_get_task_200.png)

**PATCH /tasks/1 `{"done": true}` → 200 OK**

![PATCH /tasks/1 200](screenshots/10_patch_task_200.png)

**DELETE /tasks/2 → 204 No Content**

![DELETE /tasks/2 204](screenshots/11_delete_task_204.png)

**GET /tasks/2 после удаления → 404 Not Found**

![GET /tasks/2 404](screenshots/12_get_task_404.png)

### Таблицы в БД (`\dt` в psql)

![psql \dt](screenshots/13_psql_dt.png)

## Ответы на контрольные вопросы (практическая работа №2)

### 1. Чем FastAPI отличается от Starlette и какие компоненты Starlette он использует?

**Starlette** — лёгкий ASGI-фреймворк/тулкит: маршрутизация, запросы и ответы, middleware, WebSocket,
фоновые задачи, статические файлы, тестовый клиент. Он ничего не знает о типах данных: тело запроса
нужно разбирать и проверять вручную, документации API он не генерирует.

**FastAPI** построен поверх Starlette (класс `FastAPI` наследуется от `Starlette`) и добавляет:
- объявление параметров через аннотации типов и автоматическую валидацию/сериализацию через **Pydantic**;
- систему внедрения зависимостей **`Depends`**;
- автоматическую генерацию схемы **OpenAPI** и интерфейсов Swagger UI (`/docs`) и ReDoc (`/redoc`);
- `response_model`, коды ответа, обработку `HTTPException` и ошибок валидации (422).

Из Starlette FastAPI использует: `Request`/`Response` (и `JSONResponse`, `StreamingResponse` и др.),
маршрутизацию (`APIRouter` расширяет роутер Starlette), **middleware** (`@app.middleware("http")`,
`CORSMiddleware`, `GZipMiddleware` и т. д.), `BackgroundTasks`, WebSocket, `StaticFiles`, `TestClient`,
обработчики исключений и события жизненного цикла (lifespan).

### 2. Зачем разделять схемы Create, Read и Update?

У одной сущности разный набор полей в разных операциях:
- **Create** — то, что присылает клиент при создании: нет `id` и `created_at` (их назначает БД),
  обязательные поля действительно обязательны (`title`, `owner_id`);
- **Read** — то, что сервер возвращает: есть `id`, `created_at`, и нет ничего лишнего или секретного
  (например, хеша пароля);
- **Update** — для частичного обновления (PATCH) все поля необязательны, клиент присылает только изменяемые.

Разделение даёт безопасность (клиент не сможет подменить `id`, `created_at` или `owner_id` через PATCH),
точную валидацию для каждой операции и честную документацию OpenAPI, где для каждого эндпоинта
видно, что именно он принимает и отдаёт.

### 3. Что делает `from_attributes=True`?

Разрешает Pydantic-модели создаваться не только из словаря, но и **из атрибутов произвольного объекта**
(`UserRead.model_validate(user_orm)`), читая `obj.id`, `obj.email` и т. д. Это нужно, чтобы
FastAPI мог преобразовать возвращаемую из эндпоинта ORM-модель SQLAlchemy в схему `*Read`
по `response_model`. В Pydantic v1 эта настройка называлась `orm_mode = True`.

### 4. Почему сессия передаётся через `Depends`, а не создаётся глобально?

- **Своя сессия на каждый запрос.** `AsyncSession` не потокобезопасна и не предназначена
  для одновременного использования из нескольких корутин; глобальная сессия смешивала бы транзакции
  и состояние (identity map) разных запросов.
- **Гарантированное освобождение ресурсов.** `get_session` отдаёт сессию через `yield` внутри
  `async with`, поэтому после ответа сессия закрывается и соединение возвращается в пул, даже если
  в обработчике произошла ошибка.
- **Тестируемость.** Зависимость можно подменить через `app.dependency_overrides[get_session]`
  (тестовая БД, мок) без изменения кода эндпоинтов.
- **Слабая связанность.** Эндпоинт объявляет, что ему нужна сессия, но не знает, как она создаётся.

### 5. Чем `exclude_unset=True` отличается от `exclude_none=True`?

- `exclude_unset=True` исключает поля, которые **клиент не передал** в запросе (остались значениями
  по умолчанию «не заданы»);
- `exclude_none=True` исключает поля, **значение которых `None`**, независимо от того, передал их
  клиент или нет.

Для PATCH правильно использовать `exclude_unset`: запрос `{"description": null}` должен **очистить**
описание. С `exclude_unset` поле попадёт в обновление со значением `None`, а с `exclude_none` будет
отброшено, и очистить поле станет невозможно. При этом поля, которых не было в запросе, в обоих
случаях не трогаются.

```python
TaskUpdate(description=None).model_dump(exclude_unset=True)  # {'description': None}
TaskUpdate(description=None).model_dump(exclude_none=True)   # {}
```

### 6. Почему в production таблицы не создают через `create_all`?

`Base.metadata.create_all()` только **создаёт отсутствующие таблицы**. Он:
- не изменяет существующие таблицы — новый столбец, смена типа, индекс или ограничение не применятся;
- не умеет удалять/переименовывать столбцы и переносить данные;
- не хранит историю и версию схемы, нельзя откатиться (`downgrade`);
- не даёт просмотреть и проверить SQL перед применением, схемы на разных стендах расходятся незаметно.

Миграции (Alembic) решают это: каждое изменение схемы — версионированный файл в git с `upgrade`/`downgrade`,
текущая версия записана в таблице `alembic_version`, изменения применяются одинаково и воспроизводимо
на всех окружениях (`alembic upgrade head`), их можно проверить на ревью и откатить.

## Ответы на контрольные вопросы (практическая работа №3)

### 1. Чем CI отличается от CD (continuous delivery и continuous deployment)?

CI — это процесс постоянного обновления кода: на этапе CI проходят тесты, линтеры и т. д.
CD отвечает за доставку кода до профильной среды.

### 2. Как работает `dependency_overrides` и зачем он нужен в тестах?

`dependency_overrides` перезатирает зависимости проекта. Это нужно для работы с тестовыми данными.

### 3. Зачем нужна многоэтапная сборка образа?

Для оптимизации скорости сборки и размера образа: разные этапы могут кешироваться для ускорения сборки,
а в конечный образ попадает только последний этап.

### 4. Почему контейнер не следует запускать от root?

Контейнер — это не виртуальная машина: процессы в нём работают на ядре хоста, и без user namespaces
root внутри контейнера — это тот же UID 0, что и root на хосте. Поэтому:

- при уязвимости в ядре или container runtime, а также при неудачной конфигурации (смонтированный
  `docker.sock`, `--privileged`, тома с файлами хоста) взломанный процесс получает права root **на хосте**;
- даже без выхода из контейнера злоумышленник, захвативший приложение, может от root изменить код,
  установить свои пакеты, читать и подменять любые файлы внутри контейнера;
- это нарушает принцип наименьших привилегий: веб-приложению не нужны права root, чтобы слушать
  порт 8000 и ходить в БД;
- многие платформы (Kubernetes с `runAsNonRoot`, OpenShift) вообще не запускают контейнеры от root.

В этом проекте финальный этап Dockerfile создаёт системного пользователя `app` и переключается на него
(`USER app`), а файлы кода принадлежат root, так что приложение не может их изменить.

### 5. Как в GitHub Actions передаются секреты и почему их нельзя хранить в репозитории?

Секреты записываются на платформе GitHub. В секретах могут быть ключи, пароли и другие чувствительные
данные, которые нельзя выставлять публично.

### 6. Что произойдёт с job-ом build, если упадёт test? Где это задаётся?

Job `build` **не запустится** — он получит статус *skipped* (это видно на скриншоте «упавшего» pipeline
выше), и образ не будет собран и опубликован. Так в реестр никогда не попадает версия с непройденными тестами.

Задаётся это в `.github/workflows/ci.yml` ключом `needs`:

```yaml
build:
  needs: [lint, test]
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

Без `needs` все job-ы workflow запускаются параллельно и независимо. С `needs` job ждёт завершения
перечисленных job-ов и по умолчанию (неявное условие `success()`) запускается, только если все они
завершились успешно. Изменить это поведение можно явным условием, например `if: always()` или
`if: failure()`. Дополнительное условие `if` здесь ограничивает `build` только push-ем в `main`,
поэтому на pull request он пропускается даже при зелёных тестах.

### 7. Где лучше применять миграции: при старте контейнера или отдельным шагом в CD? Каковы плюсы и минусы каждого варианта?

**При старте контейнера** (так сделано в `docker-compose.yml`: `alembic upgrade head && exec uvicorn ...`):

- ➕ просто: не нужен отдельный шаг, схема БД всегда соответствует версии кода в образе;
- ➕ одинаково работает локально, в Compose и на одном сервере;
- ➖ при нескольких репликах миграции запускаются одновременно в каждой и могут конфликтовать
  (Alembic по умолчанию не берёт блокировку);
- ➖ долгая миграция задерживает старт и может сорвать healthcheck, а упавшая — приводит
  к циклическому перезапуску контейнера;
- ➖ приложению нужны права на изменение схемы (DDL), хотя для работы ему хватило бы прав на чтение и запись данных;
- ➖ миграции нельзя проконтролировать отдельно: нет отдельного лога, ручного подтверждения, отката перед выкаткой.

**Отдельным шагом в CD** (отдельный job, одноразовый контейнер `alembic upgrade head`, Kubernetes Job
перед обновлением подов):

- ➕ миграция выполняется ровно один раз, до выкатки новой версии; если она упала, деплой
  останавливается и старая версия продолжает работать;
- ➕ для миграций можно использовать отдельную учётную запись с правами DDL, а приложению оставить минимальные права;
- ➕ отдельные логи, возможность ручного подтверждения (environments с approval) и бэкапа перед миграцией;
- ➖ pipeline сложнее: CD нужен сетевой доступ к БД и её учётные данные;
- ➖ между миграцией и выкаткой новой версии работает старый код, поэтому миграции нужно писать
  обратно совместимыми (схема expand/contract: сначала добавить столбец, потом убрать старый).

**Вывод:** для локальной разработки и одного экземпляра приложения удобно применять миграции при старте
контейнера (как в этом проекте). Для production с несколькими репликами лучше отдельный шаг в CD.
