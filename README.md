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

### Сброс стенда к тестовым данным
```powershell
.\infra\reset.ps1
```
Тестовые пользователи (пароль `Passw0rd!`):

| email | RUB | USD |
|---|---|---|
| alice@example.com | 100 000.00 | 1 000.00 |
| bob@example.com | 50 000.00 | 0 |
| carol@example.com | 0 | 0 |

### Адреса
| Что | URL |
|---|---|
| API / Swagger | http://localhost:8000/docs |
| WireMock admin | http://localhost:8089/__admin/mappings |
| PostgreSQL | localhost:5432, db/user/password `payflow` |

## Бизнес-правила
- Комиссия 1% от суммы перевода, минимум 10 RUB, максимум 500 RUB (для USD-счета границы пересчитываются по курсу). Комиссия списывается сверх суммы.
- Конвертация по курсу USD/RUB из сервиса курсов (WireMock), округление до 0.01 по ROUND_HALF_UP.
- Суточный лимит исходящих переводов — 300 000 RUB в рублевом эквиваленте (сутки по UTC).
- Сумма: > 0, ≤ 1 000 000, не больше 2 знаков после запятой.
- Антифрод (WireMock): сумма `77777.00` RUB → отказ (403), `66666.00` RUB → таймаут (503).
- Недоступный сервис курсов или антифрода → 503.
- Чужой или несуществующий счет → 404.

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
- [x] День 2: регистрация, JWT, счета, переводы с комиссией и конвертацией, лимит, WireMock (курсы, антифрод)
