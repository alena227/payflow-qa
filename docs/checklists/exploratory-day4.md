# Ручное тестирование — день 4

Стенд в режиме сборки-кандидата: `$env:BUGS='1'; docker compose up -d; Remove-Item Env:BUGS`, затем `.\infra\reset.ps1`.

## 1. Прогон тест-кейсов в Qase (≈2 ч)
1. Qase → проект PayFlow → **Test Runs → Start new test run** → выбрать все кейсы, назвать «Manual run 1 — BUGS=1».
2. Идти по кейсам по порядку сюит. Для каждого: **Passed / Failed / Blocked / Skipped**.
3. Failed → кнопка **Create defect** в Qase (или сразу файл `docs/bugs/BUG-NNN.md`) — фактический vs ожидаемый результат, request_id.
4. В конце: **Complete run** → экспорт отчета (PDF/CSV) в `docs/qase/`.

Порядок, который экономит время: Авторизация → Счета → Переводы (комиссия, конвертация, лимит) → Внешние сервисы → История → Безопасность → Kafka → БД → UI → мобильная версия.

## 2. Исследовательские сессии (≈1 ч, 2 × 30 мин)
Формат сессии: **миссия → заметки → найденное → вопросы**. Записывай сюда.

### Сессия 1. Деньги: «Могу ли я заставить систему посчитать неправильно?»
- суммы около границ комиссии и лимита, копейки, конвертация туда-обратно
- сверяй каждый ответ с ручным расчетом (калькулятор / Python `Decimal`)
- после серии переводов сверь балансы с историей

Заметки:

Найдено:

Вопросы к «аналитику»:

### Сессия 2. Доступ: «Могу ли я увидеть или сделать то, что мне нельзя?»
- чужие id в путях и телах запросов, токены, 2FA, CORS
- UI на телефоне (DevTools → Device Toolbar)

Заметки:

Найдено:

Вопросы:

## 3. Полезное
- Swagger: http://localhost:8000/docs (кнопка Authorize → вставить токен)
- Kafka: http://localhost:8081 (нужен `docker compose --profile tools up -d`)
- Логи: http://localhost:8888, поиск по request_id
- БД: `docker compose exec postgres psql -U payflow` (или DBeaver: localhost:5432, payflow/payflow)
- JWT: https://jwt.io
- Ожидаемая комиссия в Python:
  ```python
  from decimal import Decimal as D, ROUND_HALF_UP
  fee = min(max(D("1250.50") * D("0.01"), D(10)), D(500)).quantize(D("0.01"), ROUND_HALF_UP)
  ```
