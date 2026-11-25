# PayFlow QA

Учебный стенд мини-кошелька. **Приложение — учебный стенд, фокус проекта на тестировании**: API, PostgreSQL, Kafka, безопасность, UI, Java-автотесты, нагрузка, логи, тестирование ИИ.

## Стек
FastAPI · PostgreSQL · Redpanda (Kafka API) · WireMock · Docker Compose · pytest · Playwright · Java (JUnit 5, Rest Assured, Cucumber) · k6 · GitHub Actions · Jenkins · Allure

## Архитектура
```
 web (nginx, :8090) ──HTTP──▶ api (FastAPI, :8000) ──SQL──▶ postgres
                                │   │
                     курсы,     │   └── событие transfer.completed ──▶ Kafka/Redpanda: transactions
                     антифрод ◀─┘                                           │
                     (WireMock)                         notifier ◀──────────┘
                                                          │  ├─▶ notifications (postgres)
                                                          │  └─▶ transactions.dlq (битые сообщения)
```

## Быстрый старт
Нужен Docker Desktop.

```powershell
copy .env.example .env
docker compose up -d --build
.\infra\reset.ps1
```

Проверка: http://localhost:8000/health → `{"status":"ok","db":"ok"}`

Остановить: `docker compose down`. Остановить и стереть данные: `docker compose down -v`.

### Режим со скрытыми багами
В файле `.env` поставь `BUGS=1` и выполни `docker compose up -d` (или `docker compose --profile tools up -d`).
Вернуть нормальный режим: `BUGS=0` в `.env` и снова `docker compose up -d`. Режим хранится в `.env`, поэтому не слетает при перезапусках.
Список багов спрятан в `docs/.answers.md`.

### Вспомогательные инструменты (профиль tools)
```powershell
docker compose --profile tools up -d
```

### Сброс стенда к тестовым данным
```powershell
.\infra\reset.ps1
```
Тестовые пользователи (пароль `Passw0rd!`):

| email | RUB | USD | Примечание |
|---|---|---|---|
| alice@example.com | 100 000.00 | 1 000.00 | |
| bob@example.com | 50 000.00 | 0 | |
| carol@example.com | 0 | 0 | пустые счета |
| dave@example.com | 10 000.00 | 100.00 | 2FA включена, TOTP-секрет `JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP` |

### Адреса
| Что | URL |
|---|---|
| Веб-интерфейс | http://localhost:8090 |
| API / Swagger | http://localhost:8000/docs |
| WireMock admin | http://localhost:8089/__admin/mappings |
| Kafka (Redpanda) для тестов | localhost:19092 |
| PostgreSQL | localhost:5432, db/user/password `payflow` |
| Dozzle, логи (tools) | http://localhost:8888 |
| Redpanda Console (tools) | http://localhost:8081 |

## Бизнес-правила
- Комиссия 1% от суммы перевода, минимум 10 RUB, максимум 500 RUB (для USD-счета границы пересчитываются по курсу). Комиссия списывается сверх суммы.
- Конвертация по курсу USD/RUB из сервиса курсов (WireMock), округление до 0.01 по ROUND_HALF_UP.
- Суточный лимит исходящих переводов — 300 000 RUB в рублевом эквиваленте (сутки по UTC).
- Сумма: > 0, ≤ 1 000 000, не больше 2 знаков после запятой.
- Антифрод (WireMock): сумма `77777.00` RUB → отказ (403), `66666.00` RUB → таймаут (503).
- Недоступный сервис курсов или антифрода → 503.
- Чужой или несуществующий счет → 404.
- Вход: 5 неудачных попыток подряд (пароль или код 2FA) → блокировка на 5 минут (429).
- 2FA (TOTP): `/auth/2fa/setup` → `/auth/2fa/enable`; при включенной 2FA вход требует поле `otp`.
- Каждый перевод публикует событие в топик `transactions` (ключ — `tx_id`, схема: [`app/notifier/transaction_event.schema.json`](app/notifier/transaction_event.schema.json)). notifier создает уведомления отправителю и получателю, невалидные сообщения уходят в `transactions.dlq`.
- CORS разрешен только для `http://localhost:8090`.
- Логи всех сервисов в JSON, сквозной `request_id` (заголовок `X-Request-ID`) проходит через api, WireMock и Kafka.

## Структура
```
app/         приложение: api, notifier, web
infra/       wiremock, скрипт сброса
docs/        требования, тест-план, чек-листы, отчеты, баг-репорты
tests/       pytest: api, db, kafka, security, llm, ui
java-tests/  JUnit 5, Rest Assured, Cucumber
load/        k6
```

## Статус
- [x] День 1: каркас, PostgreSQL, `/health`
- [x] День 2: регистрация, JWT, счета, переводы с комиссией и конвертацией, лимит, WireMock (курсы, антифрод)
- [x] День 3: Kafka (Redpanda), notifier + DLQ, 2FA, блокировка входа, CORS, веб-интерфейс, режим `BUGS=1`
- [x] День 4: [требования](docs/requirements.md), [тест-план](docs/test-plan.md), [60 тест-кейсов](docs/test-cases.md) (+ импорт в Qase), [чек-лист безопасности](docs/checklists/security.md), [шаблон баг-репорта](docs/bugs/_template.md)
