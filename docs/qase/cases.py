"""Единый источник тест-кейсов PayFlow.

Из этого файла скрипт build.py генерирует:
- docs/test-cases.md        — читаемый список для репозитория;
- docs/qase/qase-import.csv — файл для импорта в Qase.

Курс в WireMock: USD/RUB = 92.4750. Тестовые пользователи — см. README (пароль Passw0rd!).
Счета после .\\infra\\reset.ps1: alice RUB=№3, USD=№4; bob RUB=№5, USD=№6; carol RUB=№7, USD=№8; dave RUB=№9, USD=№10.
"""

SUITES = [
    "Авторизация",
    "2FA",
    "Счета",
    "Переводы: комиссия",
    "Переводы: конвертация",
    "Переводы: лимит и валидация",
    "Внешние сервисы",
    "История и уведомления",
    "Kafka",
    "Данные (БД)",
    "Безопасность",
    "UI",
    "UI: мобильная версия",
]

PRE_RESET = "Стенд поднят, выполнен .\\infra\\reset.ps1"
PRE_ALICE = PRE_RESET + "; получен токен alice@example.com (POST /auth/login)"


def c(id, suite, title, req, steps, pre=PRE_RESET, priority="medium", severity="normal",
      type="functional", behavior="positive", layer="api", automation="to-be-automated"):
    return dict(id=id, suite=suite, title=title, req=req, steps=steps, pre=pre, priority=priority,
                severity=severity, type=type, behavior=behavior, layer=layer, automation=automation)


CASES = [
    # ---------------- Авторизация ----------------
    c("TC-001", "Авторизация", "Регистрация с валидными данными", "REQ-AUTH-01, REQ-AUTH-02", [
        ("POST /auth/register {email: new1@example.com, password: Secret123}", "201, в ответе id и email new1@example.com"),
        ("Войти этим пользователем, GET /accounts", "Два счета: RUB и USD, balance \"0.00\""),
    ], priority="high", severity="critical", type="smoke"),
    c("TC-002", "Авторизация", "Повторная регистрация с тем же email (в другом регистре)", "REQ-AUTH-01", [
        ("POST /auth/register {email: ALICE@example.com, password: Secret123}", "409 email already registered"),
    ], behavior="negative", severity="major"),
    c("TC-003", "Авторизация", "Регистрация: граничные значения длины пароля", "REQ-AUTH-01", [
        ("Пароль из 7 символов", "422"),
        ("Пароль из 8 символов", "201"),
        ("Пароль из 64 символов", "201"),
        ("Пароль из 65 символов", "422"),
    ], behavior="negative"),
    c("TC-004", "Авторизация", "Регистрация с невалидным email", "REQ-AUTH-01", [
        ("email: \"alice\", \"alice@\", \"@example.com\", пустая строка", "422 для каждого значения, пользователь не создан"),
    ], behavior="negative", severity="minor"),
    c("TC-005", "Авторизация", "Вход с верными данными", "REQ-AUTH-03, REQ-AUTH-04", [
        ("POST /auth/login {alice@example.com, Passw0rd!}", "200, access_token, token_type = bearer"),
        ("Декодировать токен на jwt.io", "header alg = HS256; payload содержит sub, iat, exp; exp − iat = 1800 c"),
    ], priority="high", severity="critical", type="smoke"),
    c("TC-006", "Авторизация", "Вход с неверным паролем и с несуществующим email", "REQ-AUTH-03", [
        ("Вход alice@example.com с паролем wrong", "401 invalid credentials"),
        ("Вход nobody@example.com с паролем Passw0rd!", "401 с тем же текстом invalid credentials"),
    ], priority="high", behavior="negative", severity="major", type="security"),
    c("TC-007", "Авторизация", "Запрос защищенного эндпоинта без токена и с битым токеном", "REQ-AUTH-05", [
        ("GET /accounts без заголовка Authorization", "401"),
        ("GET /accounts с Authorization: Bearer abc.def.ghi", "401 invalid token"),
    ], priority="high", behavior="negative", severity="critical", type="security"),
    c("TC-008", "Авторизация", "Блокировка после 5 неудачных попыток входа", "REQ-AUTH-06", [
        ("5 раз войти как carol с неверным паролем", "Каждый раз 401"),
        ("Войти как carol с верным паролем", "429 too many failed attempts"),
        ("Выполнить reset.ps1 (или подождать 5 минут) и войти с верным паролем", "200"),
    ], priority="high", behavior="negative", severity="major", type="security"),
    c("TC-009", "Авторизация", "Успешный вход сбрасывает счетчик неудачных попыток", "REQ-AUTH-06", [
        ("4 раза неверный пароль carol", "401"),
        ("1 раз верный пароль", "200"),
        ("Еще 4 раза неверный пароль, затем верный", "Последний вход 200 (блокировки нет)"),
    ], type="security"),

    # ---------------- 2FA ----------------
    c("TC-010", "2FA", "Подключение 2FA: setup + enable верным кодом", "REQ-2FA-01", [
        ("Токен bob, POST /auth/2fa/setup", "200, secret и otpauth_uri"),
        ("Добавить secret в Google Authenticator (или pyotp), POST /auth/2fa/enable {code}", "204"),
        ("Вход bob без otp", "401 otp required"),
    ], priority="high", severity="critical"),
    c("TC-011", "2FA", "Включение 2FA неверным кодом", "REQ-2FA-01", [
        ("setup, затем enable с кодом 000000", "400 invalid otp"),
        ("Вход bob без otp", "200 — 2FA не включилась"),
    ], behavior="negative", severity="major"),
    c("TC-012", "2FA", "Вход с включенной 2FA: таблица решений по полю otp", "REQ-2FA-02", [
        ("dave: otp не передан", "401 otp required"),
        ("dave: otp = верный код из приложения (секрет JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP)", "200, токен"),
        ("dave: otp = 123456 (неверный)", "401 invalid otp"),
        ("dave: otp = \"\" (пустая строка)", "401 invalid otp"),
        ("dave: otp = null", "401 otp required"),
    ], priority="high", severity="critical", type="security"),
    c("TC-013", "2FA", "Неверные коды 2FA учитываются в блокировке входа", "REQ-AUTH-06, REQ-2FA-02", [
        ("5 раз войти как dave с верным паролем и неверным otp", "401 invalid otp"),
        ("Вход dave с верным паролем и верным otp", "429"),
    ], behavior="negative", severity="major", type="security"),
    c("TC-014", "2FA", "Отключение 2FA только с верным кодом", "REQ-2FA-04", [
        ("Токен dave, POST /auth/2fa/disable {code: 000000}", "400"),
        ("POST /auth/2fa/disable с верным кодом", "204"),
        ("Вход dave без otp", "200"),
    ], severity="major"),

    # ---------------- Счета ----------------
    c("TC-015", "Счета", "Список счетов текущего пользователя", "REQ-ACC-01, REQ-ACC-04", [
        ("Токен alice, GET /accounts", "Ровно 2 счета alice: RUB 100000.00 и USD 1000.00; суммы — строки с 2 знаками"),
    ], pre=PRE_ALICE, priority="high", severity="critical", type="smoke"),
    c("TC-016", "Счета", "Получение своего счета по id", "REQ-ACC-02", [
        ("Токен alice, GET /accounts/3", "200, currency RUB, balance 100000.00"),
    ], pre=PRE_ALICE),
    c("TC-017", "Счета", "Пополнение счета: валидные и граничные суммы", "REQ-ACC-03", [
        ("POST /accounts/3/topup {amount: \"0.01\"}", "201, баланс +0.01, в истории операция topup"),
        ("amount: \"1000000\"", "201"),
        ("amount: \"0\", \"-1\", \"1000000.01\", \"1.001\"", "422 для каждого, баланс не изменился"),
    ], pre=PRE_ALICE, behavior="negative"),
    c("TC-018", "Счета", "Пополнение чужого счета", "REQ-ACC-03, REQ-SEC-01", [
        ("Токен alice, POST /accounts/5/topup {amount: 100}", "404, баланс bob не изменился"),
    ], pre=PRE_ALICE, behavior="negative", severity="critical", type="security"),

    # ---------------- Переводы: комиссия ----------------
    c("TC-019", "Переводы: комиссия", "Перевод RUB→RUB: успешный сценарий", "REQ-TRF-01, REQ-TRF-03", [
        ("Токен alice, POST /transfers {from 3, to 5, amount \"5000\"}", "201, fee 50.00, amount_to 5000.00, rate null"),
        ("GET /accounts (alice) и GET /accounts (bob)", "alice RUB 94950.00 (−5000 − 50), bob RUB 55000.00"),
    ], pre=PRE_ALICE, priority="high", severity="blocker", type="smoke"),
    c("TC-020", "Переводы: комиссия", "Минимальная комиссия 10 ₽: граничные значения", "REQ-TRF-03", [
        ("Перевод 0.01 ₽", "fee 10.00"),
        ("Перевод 999.99 ₽", "fee 10.00"),
        ("Перевод 1000.00 ₽", "fee 10.00"),
        ("Перевод 1000.01 ₽", "fee 10.00"),
        ("Перевод 1100.00 ₽", "fee 11.00"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-021", "Переводы: комиссия", "Максимальная комиссия 500 ₽: граничные значения", "REQ-TRF-03", [
        ("Перевод 49999.99 ₽", "fee 500.00 (499.9999 → 500.00)"),
        ("Перевод 50000.00 ₽", "fee 500.00"),
        ("Перевод 50000.01 ₽", "fee 500.00"),
        ("Пополнить счет, перевод 75000.00 ₽", "fee 500.00"),
    ], pre=PRE_ALICE + "; при нехватке средств пополнить счет 3 через topup", priority="high", severity="critical"),
    c("TC-022", "Переводы: комиссия", "Округление комиссии ROUND_HALF_UP", "REQ-TRF-03", [
        ("Перевод 1234.56 ₽", "fee 12.35 (12.3456)"),
        ("Перевод 1250.50 ₽", "fee 12.51 (12.505 — половина округляется вверх)"),
        ("Перевод 1234.40 ₽", "fee 12.34 (12.344)"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-023", "Переводы: комиссия", "Комиссия для USD-счета пересчитывается по курсу", "REQ-TRF-03, REQ-TRF-04", [
        ("Перевод 10.00 USD со счета 4 на счет 6", "fee 0.11 (мин. 10 ₽ / 92.475 = 0.10814 → 0.11)"),
        ("Перевод 100.00 USD", "fee 1.00 (1% от 9247.50 ₽ = 92.475 ₽ → 1.00 $)"),
        ("Перевод 700.00 USD", "fee 5.41 (макс. 500 ₽ / 92.475 = 5.4069 → 5.41)"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-024", "Переводы: комиссия", "Комиссия зачисляется на системный счет", "REQ-TRF-09", [
        ("Запомнить баланс системного RUB-счета: SELECT balance FROM accounts a JOIN users u ON u.id=a.user_id WHERE u.is_system AND currency='RUB'", "Значение X"),
        ("Перевод 5000 ₽ alice → bob", "fee 50.00"),
        ("Повторить SELECT", "X + 50.00"),
    ], pre=PRE_ALICE, layer="api", severity="major"),

    # ---------------- Переводы: конвертация ----------------
    c("TC-025", "Переводы: конвертация", "Перевод USD→RUB с конвертацией", "REQ-TRF-04", [
        ("Перевод 10.00 USD со счета 4 на счет 5", "201, rate 92.475000, amount_to 924.75, currency_to RUB"),
        ("Балансы", "alice USD 989.89 (−10 −0.11), bob RUB 50924.75"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-026", "Переводы: конвертация", "Перевод RUB→USD с конвертацией", "REQ-TRF-04", [
        ("Перевод 1000.00 ₽ со счета 3 на счет 6", "amount_to 10.81 (1000 / 92.475 = 10.8137), fee 10.00 ₽"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-027", "Переводы: конвертация", "Округление при конвертации (третий знак ≥ 5)", "REQ-TRF-04", [
        ("Перевод 10.01 USD на RUB-счет", "amount_to 925.67 (925.67475)"),
        ("Перевод 0.07 USD на RUB-счет", "amount_to 6.47 (6.47325)"),
        ("Перевод 50.00 ₽ на USD-счет", "amount_to 0.54 (0.540686)"),
    ], pre=PRE_ALICE, severity="critical"),
    c("TC-028", "Переводы: конвертация", "Перевод между своими счетами разной валюты", "REQ-TRF-01, REQ-HIST-01", [
        ("Перевод 1000 ₽ со счета 3 на свой USD-счет 4", "201, amount_to 10.81"),
        ("GET /transactions", "Операция с direction = self"),
    ], pre=PRE_ALICE),

    # ---------------- Переводы: лимит и валидация ----------------
    c("TC-029", "Переводы: лимит и валидация", "Суточный лимит: ровно 300 000 ₽ разрешено", "REQ-TRF-05", [
        ("Пополнить счет 3 на 300000", "201"),
        ("Перевод 300000.00 ₽ на счет 5", "201 (итог за сутки = лимиту)"),
        ("Перевод 0.01 ₽", "422 daily transfer limit exceeded"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-030", "Переводы: лимит и валидация", "Суточный лимит: сумма нескольких переводов", "REQ-TRF-05", [
        ("Пополнить счет 3 на 300000; перевод 200000 ₽", "201"),
        ("Перевод 100000.01 ₽", "422, балансы не изменились"),
        ("Перевод 100000.00 ₽", "201"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-031", "Переводы: лимит и валидация", "Лимит учитывает переводы со всех счетов (RUB и USD)", "REQ-TRF-05", [
        ("Пополнить USD-счет 4 на 3000; перевод 3000 USD (= 277 425 ₽)", "201"),
        ("Пополнить счет 3; перевод 30000 ₽ (итого 307 425 ₽)", "422 daily transfer limit exceeded"),
    ], pre=PRE_ALICE, priority="high", severity="critical"),
    c("TC-032", "Переводы: лимит и валидация", "Недостаточно средств с учетом комиссии", "REQ-TRF-06", [
        ("carol (баланс 0): перевод 1 ₽", "422 insufficient funds"),
        ("dave (RUB 10000): перевод 9995 ₽ (нужно 9995 + 99.95)", "422 insufficient funds"),
        ("dave: перевод 9900 ₽ (нужно 9900 + 99 = 9999)", "201, остаток 1.00"),
    ], priority="high", behavior="negative", severity="critical"),
    c("TC-033", "Переводы: лимит и валидация", "Валидация суммы перевода", "REQ-TRF-02", [
        ("amount: \"0\", \"-100\", \"0.001\", \"1000000.01\", \"abc\", пустая строка, null", "422 для каждого"),
        ("amount: \"0.01\" и \"1000000\" (при достаточном балансе/лимите)", "0.01 — 201; 1000000 — 422 из-за лимита, но не из-за валидации"),
    ], pre=PRE_ALICE, behavior="negative", severity="major"),
    c("TC-034", "Переводы: лимит и валидация", "Перевод на тот же счет и на несуществующий счет", "REQ-TRF-01", [
        ("from 3, to 3", "422 cannot transfer to the same account"),
        ("from 3, to 99999", "404 destination account not found"),
        ("from 3, to 1 (системный счет комиссий)", "404"),
    ], pre=PRE_ALICE, behavior="negative"),
    c("TC-035", "Переводы: лимит и валидация", "Перевод с чужого счета", "REQ-TRF-01, REQ-SEC-01", [
        ("Токен alice, from 5 (счет bob), to 3", "404 source account not found, балансы не изменились"),
    ], pre=PRE_ALICE, priority="high", behavior="negative", severity="blocker", type="security"),
    c("TC-036", "Переводы: лимит и валидация", "Параллельные переводы не уводят баланс в минус", "REQ-TRF-08, REQ-DATA-02", [
        ("dave (RUB 10000): одновременно отправить 5 запросов перевода по 3000 ₽ (Postman Runner / скрипт)", "Успешны не больше 3, остальные 422 insufficient funds"),
        ("GET /accounts dave", "Баланс ≥ 0 и равен 10000 − успешные × 3030"),
    ], behavior="destructive", severity="critical", automation="to-be-automated"),

    # ---------------- Внешние сервисы ----------------
    c("TC-037", "Внешние сервисы", "Отказ антифрода", "REQ-TRF-07", [
        ("Перевод 77777.00 ₽ (стаб WireMock: deny)", "403 transfer rejected by antifraud"),
        ("Балансы и история", "Без изменений"),
    ], pre=PRE_ALICE, priority="high", behavior="negative", severity="critical", type="integration"),
    c("TC-038", "Внешние сервисы", "Таймаут антифрода", "REQ-TRF-07", [
        ("Перевод 66666.00 ₽ (стаб: задержка 5 c, таймаут клиента 2 c)", "503 antifraud service timeout примерно через 2 c"),
        ("Балансы", "Без изменений"),
    ], pre=PRE_ALICE, behavior="negative", severity="major", type="integration"),
    c("TC-039", "Внешние сервисы", "Сервис курсов недоступен", "REQ-TRF-07", [
        ("Через WireMock admin (POST /__admin/mappings) добавить стаб GET /rates/USD/RUB → 500 с priority 1", "201"),
        ("Перевод USD→RUB", "503 rates service unavailable"),
        ("Перевод RUB→RUB", "201 — курс не нужен"),
        ("POST /__admin/reset", "Стабы восстановлены"),
    ], pre=PRE_ALICE, behavior="negative", severity="major", type="integration"),
    c("TC-040", "Внешние сервисы", "Сервис курсов вернул некорректный курс", "REQ-TRF-07", [
        ("Стаб: {\"rate\": \"abc\"}, затем {\"rate\": \"0\"}, затем {\"rate\": \"-1\"}, затем ответ без поля rate", "Перевод USD→RUB → 503 в каждом случае, балансы без изменений"),
    ], pre=PRE_ALICE, behavior="negative", severity="major", type="integration"),

    # ---------------- История и уведомления ----------------
    c("TC-041", "История и уведомления", "История операций: состав, порядок, direction", "REQ-HIST-01", [
        ("alice: перевод bob 100 ₽; bob: перевод alice 50 ₽", "201, 201"),
        ("GET /transactions (alice)", "Сверху входящая 50 (direction in), затем исходящая 100 (out), затем topup; чужих операций нет"),
    ], pre=PRE_ALICE, severity="major"),
    c("TC-042", "История и уведомления", "Пагинация истории", "REQ-HIST-01", [
        ("Сделать 5 переводов; GET /transactions?limit=2&offset=0, затем offset=2", "По 2 записи, без пересечений"),
        ("limit=0, limit=201, offset=-1", "422"),
    ], pre=PRE_ALICE, severity="minor"),
    c("TC-043", "История и уведомления", "Уведомления отправителю и получателю", "REQ-HIST-02", [
        ("alice: перевод 1000 ₽ на счет bob", "201"),
        ("Через 3 c GET /notifications (alice)", "Сообщение «Перевод 1000.00 RUB на счет #5 выполнен. Комиссия 10.00 RUB»"),
        ("GET /notifications (bob)", "Сообщение «Поступление 1000.00 RUB со счета #3»"),
    ], pre=PRE_ALICE, priority="high", severity="major", type="integration"),

    # ---------------- Kafka ----------------
    c("TC-044", "Kafka", "Событие перевода публикуется ровно один раз", "REQ-EVT-01", [
        ("Выполнить перевод RUB→RUB и перевод RUB→USD, запомнить tx_id", "201"),
        ("Redpanda Console → Topics → transactions → найти сообщения по key = tx_id", "Для каждого tx_id ровно 1 сообщение"),
    ], pre=PRE_ALICE, priority="high", severity="critical", type="integration"),
    c("TC-045", "Kafka", "Событие соответствует схеме и данным операции", "REQ-EVT-02", [
        ("Взять сообщение перевода USD→RUB из топика", "Валидно по transaction_event.schema.json: все поля, суммы — строки с 2 знаками"),
        ("Сравнить с ответом API и строкой в transactions (БД)", "amount, fee, amount_to, currency, rate совпадают; заголовок request_id = X-Request-ID ответа"),
    ], pre=PRE_ALICE, priority="high", severity="critical", type="integration"),
    c("TC-046", "Kafka", "Невалидный JSON уходит в DLQ", "REQ-EVT-04", [
        ("Redpanda Console → transactions → Produce: значение «not a json»", "Сообщение отправлено"),
        ("Открыть топик transactions.dlq", "Появилось сообщение «not a json» с заголовком error"),
        ("Сделать обычный перевод", "Уведомление пришло — notifier не завис"),
    ], severity="major", type="integration", behavior="negative"),
    c("TC-047", "Kafka", "Сообщение не по схеме уходит в DLQ", "REQ-EVT-04", [
        ("Produce в transactions: {\"event_id\": \"x\"}", "Сообщение в transactions.dlq, заголовок error содержит описание нарушения схемы"),
    ], severity="major", type="integration", behavior="negative"),
    c("TC-048", "Kafka", "Повтор события не создает дублей уведомлений", "REQ-EVT-03", [
        ("Скопировать значение события перевода из топика и отправить его в transactions повторно", "Сообщение отправлено"),
        ("SELECT count(*) FROM notifications WHERE event_id = '<event_id>'", "2 (debit + credit), а не 4"),
    ], severity="major", type="integration"),

    # ---------------- Данные ----------------
    c("TC-049", "Данные (БД)", "Балансы сходятся с историей операций", "REQ-DATA-01", [
        ("Выполнить переводы RUB→RUB, USD→RUB, RUB→USD", "201"),
        ("SQL с CTE: для каждого счета balance = Σ зачислений (amount_to) + Σ комиссий на счет − Σ списаний (amount + fee)", "Расхождений нет (0 строк)"),
    ], pre=PRE_ALICE, priority="high", severity="critical", type="integration", layer="unknown"),
    c("TC-050", "Данные (БД)", "Нет отрицательных балансов и денег в float", "REQ-DATA-02, REQ-DATA-03", [
        ("SELECT * FROM accounts WHERE balance < 0", "0 строк"),
        ("SELECT column_name, data_type FROM information_schema.columns WHERE table_name IN ('accounts','transactions') AND column_name IN ('balance','amount','fee','amount_to')", "Везде numeric"),
    ], severity="critical", layer="unknown"),

    # ---------------- Безопасность ----------------
    c("TC-051", "Безопасность", "IDOR: чтение чужого счета по id", "REQ-ACC-02, REQ-SEC-01", [
        ("Токен alice, GET /accounts/5 (счет bob)", "404 account not found, баланс bob не раскрыт"),
        ("GET /accounts/99999", "404 с тем же текстом"),
    ], pre=PRE_ALICE, priority="high", behavior="negative", severity="critical", type="security"),
    c("TC-052", "Безопасность", "JWT: истекший токен и токен с измененной подписью/payload", "REQ-AUTH-04", [
        ("Сгенерировать токен с exp в прошлом, подписанный тем же секретом (jwt.io, секрет dev-secret-change-me)", "GET /auth/me → 401"),
        ("Взять валидный токен alice, поменять sub на 3 в payload, подпись не трогать", "401"),
        ("Подписать токен другим секретом", "401"),
    ], priority="high", behavior="negative", severity="critical", type="security"),
    c("TC-053", "Безопасность", "JWT: alg = none", "REQ-AUTH-04", [
        ("Собрать токен header {\"alg\":\"none\",\"typ\":\"JWT\"}, payload {\"sub\":\"2\",\"exp\":9999999999}, пустая подпись (base64url, «xxx.yyy.»)", "GET /auth/me → 401"),
    ], priority="high", behavior="negative", severity="critical", type="security"),
    c("TC-054", "Безопасность", "CORS: чужой Origin", "REQ-SEC-02", [
        ("curl -i http://localhost:8000/health -H \"Origin: https://evil.example\"", "Нет заголовка Access-Control-Allow-Origin"),
        ("То же с Origin: http://localhost:8090", "Access-Control-Allow-Origin: http://localhost:8090"),
        ("Preflight: OPTIONS /transfers с Origin evil + Access-Control-Request-Method: POST", "Не разрешено (400 / без ACAO)"),
    ], priority="high", behavior="negative", severity="major", type="security"),

    # ---------------- UI ----------------
    c("TC-055", "UI", "Вход через веб-интерфейс и отображение данных", "REQ-UI-01, REQ-UI-02", [
        ("Открыть http://localhost:8090, войти alice@example.com / Passw0rd!", "Видны email в шапке, 2 счета с балансами, история, уведомления"),
        ("Выйти, войти с неверным паролем", "Сообщение «Неверный email или пароль»"),
    ], priority="high", severity="critical", type="smoke", layer="e2e"),
    c("TC-056", "UI", "Вход с 2FA через веб-интерфейс", "REQ-UI-01, REQ-2FA-02", [
        ("Ввести dave@example.com / Passw0rd!, нажать «Войти»", "Появилось поле «Код из приложения 2FA» и подсказка"),
        ("Ввести неверный код", "«Неверный код»"),
        ("Ввести верный код", "Открылся кабинет dave"),
    ], priority="high", severity="critical", layer="e2e"),
    c("TC-057", "UI", "Перевод через веб-интерфейс", "REQ-UI-02, REQ-HIST-02", [
        ("alice: со счета №3 на счет 5, сумма 1234,56 (с запятой)", "«Готово: 1 234.56 ₽, комиссия 12.35 ₽»"),
        ("Посмотреть счета и историю", "Баланс RUB уменьшился на 1246.91, сверху новая операция"),
        ("Подождать 2 c", "Появилось уведомление о переводе"),
        ("Перевод суммы больше баланса", "Красное сообщение об ошибке, балансы не изменились"),
    ], priority="high", severity="critical", type="smoke", layer="e2e"),
    c("TC-058", "UI: мобильная версия", "Мобильная верстка: iPhone 13 (390×844) и Pixel 7 (412×915)", "REQ-UI-03", [
        ("DevTools → Device Toolbar → iPhone 13, войти alice", "Нет горизонтальной прокрутки страницы"),
        ("Форма перевода", "Поля и кнопка «Перевести» помещаются по ширине, кнопка во всю ширину"),
        ("История", "Суммы и комиссии видны полностью"),
        ("Повторить для Pixel 7 и для ширины 360 px", "То же"),
    ], priority="high", severity="major", type="compatibility", layer="e2e"),
    c("TC-059", "UI: мобильная версия", "Мобильная версия: перевод и вход с 2FA", "REQ-UI-01, REQ-UI-03", [
        ("Эмуляция iPhone 13: вход dave с 2FA", "Поле кода видно, клавиатура цифровая (inputmode=numeric)"),
        ("Перевод 100 ₽ на счет 3", "Результат перевода виден без горизонтальной прокрутки"),
    ], severity="major", type="compatibility", layer="e2e"),
    c("TC-060", "UI", "Сквозной request_id: поиск запроса в логах", "REQ-NFR-01", [
        ("В DevTools → Network взять X-Request-ID ответа POST /transfers", "Заголовок есть"),
        ("Dozzle (http://localhost:8888) → поиск по этому id", "Строки api (request, transfer completed, event delivered) и notifier (notifications saved) с этим request_id"),
    ], severity="minor", type="other", layer="e2e", automation="is-not-automated"),
]
