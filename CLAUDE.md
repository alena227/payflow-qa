# PayFlow QA — правила проекта

PayFlow — учебный стенд мини-кошелька для QA-портфолио. **Приложение пишет Claude Code, фокус проекта — тестирование.**
Автор тестов должна понимать каждую строку тестов: всегда коротко объясняй, что и зачем делаешь. Пользователь знает Python и C++, Java не знает.

## Стек
- api: FastAPI (Python), Swagger на /docs
- PostgreSQL
- Redpanda вместо Kafka (в тестах — обычная Python-библиотека для Kafka), топики `transactions` и `transactions.dlq`
- notifier: Python, читает `transactions`, пишет уведомления в БД, битые сообщения → `transactions.dlq`
- WireMock: курсы валют и антифрод
- support-bot: бесплатный облачный LLM API, ключ в `.env`
- web: простой HTML+JS фронтенд
- Docker Compose; профили `tools` (Dozzle, Redpanda Console) и `ci` (Jenkins) запускаются по отдельности

## Ограничения
- Windows, 16 ГБ RAM. Стенд по умолчанию ≤ 2-3 ГБ памяти. WSL ограничен 6 ГБ через `%USERPROFILE%\.wslconfig`.
- Ставить `mem_limit` каждому сервису в Compose.

## Функции
- Регистрация, вход с JWT, 2FA по TOTP
- Счета RUB и USD
- Переводы между пользователями: комиссия 1% (мин 10 RUB, макс 500 RUB), конвертация по курсу из WireMock, суточный лимит, антифрод через WireMock
- История операций
- Деньги — только `Decimal` (в БД `NUMERIC`), никогда float
- Каждый перевод публикует событие в `transactions`
- Логи в JSON, в каждой строке `request_id` (заголовок `X-Request-ID`)
- Запуск: `docker compose up`; есть команда сброса стенда с тестовыми данными
- Скрытые баги включаются `BUGS=1`; их список только в `docs/.answers.md`, не упоминать в коде/комментариях/чате

## Порты (на хосте 8080 и 3000 заняты/зарезервированы Windows)
api 8000 · web 8090 · WireMock 8089 · Kafka 19092 · Postgres 5432 · Dozzle 8888 · Redpanda Console 8081

## Тестовые данные
`.\infra\reset.ps1` — alice/bob/carol/dave @example.com, пароль `Passw0rd!`, у dave 2FA (секрет в `app/api/app/seed.py`).
Домен `.test` в email не проходит валидацию pydantic — использовать `example.com`.

## Структура
- `app/` — приложение (api, notifier, support_bot, web)
- `infra/` — compose-доп. файлы, wiremock, jenkins
- `docs/` — требования, тест-план, чек-листы, отчеты, баг-репорты
- `tests/` — pytest (api, db, kafka, security, llm, ui)
- `java-tests/` — Maven, JUnit 5, Rest Assured, Cucumber, Allure
- `load/` — k6
