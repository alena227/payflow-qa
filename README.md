# PayFlow QA

Учебный стенд мини-кошелька. **Приложение — учебный стенд, фокус проекта на тестировании**: API, PostgreSQL, Kafka, безопасность, UI, Java-автотесты, нагрузка, логи, тестирование ИИ.

## Стек
FastAPI · PostgreSQL · Redpanda (Kafka API) · WireMock · Docker Compose · pytest · Playwright · Java (JUnit 5, Rest Assured, Cucumber) · k6 · GitHub Actions · Jenkins · Allure

## Быстрый старт
Нужен Docker Desktop.

```powershell
copy .env.example .env
docker compose up -d --build
```

Проверка: http://localhost:8000/health → `{"status":"ok","db":"ok"}`, Swagger: http://localhost:8000/docs

Остановить: `docker compose down`. Остановить и стереть данные: `docker compose down -v`.

## Структура
```
app/         приложение (api, notifier, support_bot, web)
infra/       wiremock, jenkins и пр.
docs/        требования, тест-план, чек-листы, отчеты, баг-репорты
tests/       pytest: api, db, kafka, security, llm, ui
java-tests/  JUnit 5, Rest Assured, Cucumber
load/        k6
```

## Статус
- [x] День 1: каркас, PostgreSQL, `/health`
