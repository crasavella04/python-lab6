# Менеджер задач — REST API на FastAPI + PostgreSQL

Практическая работа №2: REST API на **FastAPI** с хранением данных в **PostgreSQL** через **SQLAlchemy 2.0 (async)**,
валидацией через **Pydantic v2**, миграциями **Alembic** и middleware **Starlette**.

## Стек

| Компонент | Назначение |
|---|---|
| FastAPI | веб-фреймворк, роутеры, зависимости, Swagger UI |
| SQLAlchemy 2.0 + asyncpg | асинхронный ORM и драйвер PostgreSQL |
| Pydantic v2 + pydantic-settings | схемы запросов/ответов и конфигурация из окружения |
| Alembic | миграции схемы БД |
| PostgreSQL 16 (Docker) | хранилище |

## Структура проекта

```
.
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
├── screenshots/         # скриншоты для отчёта
├── alembic.ini
├── docker-compose.yml
├── requirements.txt
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

## Скриншоты

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

## Ответы на контрольные вопросы

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
