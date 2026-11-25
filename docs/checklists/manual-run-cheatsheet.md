# Шпаргалка ручного прогона: TC-029 — TC-060

Все команды PowerShell выполняются в папке проекта `C:\Users\aaaal\Projects\payflow-qa`.

**Счета:** alice RUB **3**, USD **4** · bob RUB **5**, USD **6** · carol RUB **7**, USD **8** · dave RUB **9**, USD **10**.
**Сброс стенда:** `.\infra\reset.ps1` (после сброса токены продолжают работать, балансы и счетчики — с нуля).
**Код 2FA для dave:** `pip install pyotp` (один раз), затем `python -c "import pyotp; print(pyotp.TOTP('JBSWY3DPEHPK3PXP').now())"`.

🔄 — **перед кейсом сделать сброс стенда**.

---

## Переводы: лимит и валидация (токен alice)

| Кейс | Что делать |
|---|---|
| 🔄 TC-029 | `POST /accounts/{account_id}/topup` id=3 `{"amount": "300000"}` → `POST /transfers` `{"from_account_id": 3, "to_account_id": 5, "amount": "300000.00"}` → `POST /transfers` `{"from_account_id": 3, "to_account_id": 5, "amount": "0.01"}` |
| 🔄 TC-030 | topup id=3 `{"amount": "300000"}` → transfer 3→5 `"200000"` → transfer 3→5 `"100000.01"` → проверить `GET /accounts` → transfer 3→5 `"100000.00"` |
| 🔄 TC-031 | topup id=4 `{"amount": "3000"}` → transfer `{"from_account_id": 4, "to_account_id": 6, "amount": "3000"}` → transfer 3→5 `"30000"` |
| 🔄 TC-032 | **токен carol**: transfer 7→3 `"1"` · **токен dave** (нужен otp): transfer 9→3 `"9995"`, затем 9→3 `"9900"` → `GET /accounts` |
| TC-033 | transfer 3→5 по очереди amount: `"0"`, `"-100"`, `"0.001"`, `"1000000.01"`, `"abc"`, `""`, `null`, затем `"0.01"` и `"1000000"` |
| TC-034 | transfer `{"from_account_id": 3, "to_account_id": 3, ...}`, затем `to_account_id: 99999`, затем `to_account_id: 1` (amount `"10"`) |
| TC-035 | transfer `{"from_account_id": 5, "to_account_id": 3, "amount": "10"}` (токен alice!) |
| 🔄 TC-036 | `python docs/checklists/parallel_transfers.py` (5 одновременных переводов dave по 3000) → в базе: `docker compose exec postgres psql -U payflow -c "SELECT id, balance FROM accounts WHERE id = 9;"` |

## Внешние сервисы (токен alice)

| Кейс | Что делать |
|---|---|
| TC-037 | transfer 3→5 `"77777.00"` → `GET /accounts` + `GET /transactions` (ничего не изменилось) |
| TC-038 | transfer 3→5 `"66666.00"` (ответ через ~2 c) → `GET /accounts` |
| TC-039 | Сломать курсы (команда ниже) → transfer `{"from_account_id": 4, "to_account_id": 5, "amount": "10"}` → transfer 3→5 `"10"` → **вернуть стабы** |
| TC-040 | По очереди для каждого варианта: вернуть стабы → поставить кривой курс (команды ниже) → transfer 4→5 `"10"`. В конце **вернуть стабы** |

```powershell
# TC-039: сервис курсов отвечает 500
Invoke-RestMethod -Method Post http://localhost:8089/__admin/mappings -ContentType 'application/json' -Body '{"priority":1,"request":{"method":"GET","urlPath":"/rates/USD/RUB"},"response":{"status":500}}'

# TC-040: кривые курсы (по одному, перед каждым — вернуть стабы)
Invoke-RestMethod -Method Post http://localhost:8089/__admin/mappings -ContentType 'application/json' -Body '{"priority":1,"request":{"method":"GET","urlPath":"/rates/USD/RUB"},"response":{"status":200,"jsonBody":{"rate":"abc"}}}'
Invoke-RestMethod -Method Post http://localhost:8089/__admin/mappings -ContentType 'application/json' -Body '{"priority":1,"request":{"method":"GET","urlPath":"/rates/USD/RUB"},"response":{"status":200,"jsonBody":{"rate":"0"}}}'
Invoke-RestMethod -Method Post http://localhost:8089/__admin/mappings -ContentType 'application/json' -Body '{"priority":1,"request":{"method":"GET","urlPath":"/rates/USD/RUB"},"response":{"status":200,"jsonBody":{"rate":"-1"}}}'
Invoke-RestMethod -Method Post http://localhost:8089/__admin/mappings -ContentType 'application/json' -Body '{"priority":1,"request":{"method":"GET","urlPath":"/rates/USD/RUB"},"response":{"status":200,"jsonBody":{"base":"USD"}}}'

# Вернуть стабы к исходным (из файлов infra/wiremock/mappings)
Invoke-RestMethod -Method Post http://localhost:8089/__admin/reset
```
Посмотреть текущие стабы: http://localhost:8089/__admin/mappings

## История и уведомления

| Кейс | Что делать |
|---|---|
| 🔄 TC-041 | токен alice: transfer 3→5 `"100"` · токен bob: transfer 5→3 `"50"` · токен alice: `GET /transactions` |
| TC-042 | токен alice: 5 раз transfer 3→5 `"10"` → `GET /transactions` с limit=2 offset=0, потом offset=2 → потом limit=0, limit=201, offset=-1 |
| TC-043 | токен alice: transfer 3→5 `"1000"` → подождать 3 c → `GET /notifications` (alice) → войти bob → `GET /notifications` (bob) |

## Kafka

Один раз запусти инструменты: `docker compose --profile tools up -d` → http://localhost:8081 → **Topics**.

| Кейс | Что делать |
|---|---|
| TC-044 | токен alice: transfer 3→5 `"100"` и transfer `{"from_account_id": 3, "to_account_id": 6, "amount": "1000"}`, запомни `id` из обоих ответов → Console → **transactions** → в поиске/фильтре найди сообщения с этими key → посчитай, сколько сообщений на каждый id |
| TC-045 | Открой сообщение перевода 3→6 (или USD→RUB) → сравни каждое поле с ответом API и с [схемой](../../app/notifier/transaction_event.schema.json): типы, формат сумм, все ли поля есть. Во вкладке **Headers** — request_id = `x-request-id` ответа |
| TC-046 | Console → **transactions** → **Produce** (Actions → Produce record) → Value: `not a json` → Produce → открой **transactions.dlq** → потом сделай обычный перевод и проверь `GET /notifications` |
| TC-047 | Produce в **transactions**: `{"event_id": "x"}` → открой **transactions.dlq**, заголовок **error** |
| TC-048 | Скопируй Value любого события перевода → Produce его же в **transactions** ещё раз → `docker compose exec postgres psql -U payflow -c "SELECT count(*) FROM notifications WHERE event_id = 'ВСТАВЬ_event_id';"` |

## Данные (БД)

| Кейс | Что делать |
|---|---|
| 🔄 TC-049 | токен alice: transfer 3→5 `"1000"`, transfer `{"from_account_id": 4, "to_account_id": 5, "amount": "10.01"}`, transfer `{"from_account_id": 3, "to_account_id": 6, "amount": "1000"}` → `Get-Content docs\checklists\sql\balance_check.sql \| docker compose exec -T postgres psql -U payflow` |
| TC-050 | `docker compose exec postgres psql -U payflow -c "SELECT * FROM accounts WHERE balance < 0;"` и `docker compose exec postgres psql -U payflow -c "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('accounts','transactions') AND column_name IN ('balance','amount','fee','amount_to');"` |

## Безопасность

| Кейс | Что делать |
|---|---|
| TC-051 | токен alice: `GET /accounts/{account_id}` id=5, потом id=99999 |
| TC-052 | **Истекший:** https://jwt.io → алгоритм HS256 → Payload `{"sub": "2", "iat": 1700000000, "exp": 1700000060}` → в поле секрета `dev-secret-change-me` → скопируй токен слева → Authorize в Swagger → `GET /auth/me`. **Подмена sub:** вставь свой токен на jwt.io, поменяй `"sub": "2"` на `"3"`, НЕ трогая секрет-поле (оставь пустым/любым) → `GET /auth/me`. **Чужой секрет:** то же, что «истекший», но с exp 9999999999 и секретом `hacker` → `GET /auth/me` |
| TC-053 | Authorize с токеном `eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIyIiwiZXhwIjo5OTk5OTk5OTk5fQ.` (header `alg: none`, sub=2, без подписи) → `GET /auth/me` |
| TC-054 | см. команды ниже |

После TC-052/053 верни в Authorize нормальный токен (login alice).

```powershell
# TC-054: CORS
curl.exe -i http://localhost:8000/health -H "Origin: https://evil.example"
curl.exe -i http://localhost:8000/health -H "Origin: http://localhost:8090"
curl.exe -i -X OPTIONS http://localhost:8000/transfers -H "Origin: https://evil.example" -H "Access-Control-Request-Method: POST"
```
Смотри строки `access-control-allow-origin` и `access-control-allow-credentials` в ответе.

## UI — http://localhost:8090

| Кейс | Что делать |
|---|---|
| 🔄 TC-055 | Войти alice / Passw0rd! → осмотреть страницу → «Выйти» → войти с неверным паролем |
| TC-056 | Войти dave / Passw0rd! → появится поле кода → ввести `123456` → ввести верный код (pyotp) |
| TC-057 | Войти alice → перевод со счета №3 на `5`, сумма `1234,56` → смотреть сообщение, счета, историю → через 2 c уведомления → перевод суммы больше баланса (`999999`) |
| TC-058 | F12 → значок телефона (Ctrl+Shift+M) → сверху выбрать iPhone 12 Pro / задать 390×844, обновить страницу (F5) → войти alice → проверить: можно ли прокрутить страницу вбок, видна ли целиком кнопка «Перевести», видны ли суммы в истории. Повторить для 412×915 и 360×740 |
| TC-059 | В той же эмуляции: вход dave с 2FA → перевод 100 на счет 3 |
| TC-060 | F12 → вкладка Network → сделать перевод → кликнуть запрос `transfers` → Headers → Response Headers → `x-request-id` → `docker compose --profile tools up -d` → http://localhost:8888 → поиск по этому id |
