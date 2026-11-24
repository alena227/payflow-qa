# Тест-кейсы PayFlow

> Сгенерировано из `docs/qase/cases.py` скриптом `docs/qase/build.py`. Не редактировать вручную.
> Импорт в Qase: `docs/qase/qase-import.csv`.

Всего: **60**. По приоритету: high — 33, medium — 27.

## Матрица трассируемости

| Требование | Тест-кейсы |
|---|---|
| REQ-2FA-01 | TC-010, TC-011 |
| REQ-2FA-02 | TC-012, TC-013, TC-056 |
| REQ-2FA-04 | TC-014 |
| REQ-ACC-01 | TC-015 |
| REQ-ACC-02 | TC-016, TC-051 |
| REQ-ACC-03 | TC-017, TC-018 |
| REQ-ACC-04 | TC-015 |
| REQ-AUTH-01 | TC-001, TC-002, TC-003, TC-004 |
| REQ-AUTH-02 | TC-001 |
| REQ-AUTH-03 | TC-005, TC-006 |
| REQ-AUTH-04 | TC-005, TC-052, TC-053 |
| REQ-AUTH-05 | TC-007 |
| REQ-AUTH-06 | TC-008, TC-009, TC-013 |
| REQ-DATA-01 | TC-049 |
| REQ-DATA-02 | TC-036, TC-050 |
| REQ-DATA-03 | TC-050 |
| REQ-EVT-01 | TC-044 |
| REQ-EVT-02 | TC-045 |
| REQ-EVT-03 | TC-048 |
| REQ-EVT-04 | TC-046, TC-047 |
| REQ-HIST-01 | TC-028, TC-041, TC-042 |
| REQ-HIST-02 | TC-043, TC-057 |
| REQ-NFR-01 | TC-060 |
| REQ-SEC-01 | TC-018, TC-035, TC-051 |
| REQ-SEC-02 | TC-054 |
| REQ-TRF-01 | TC-019, TC-028, TC-034, TC-035 |
| REQ-TRF-02 | TC-033 |
| REQ-TRF-03 | TC-019, TC-020, TC-021, TC-022, TC-023 |
| REQ-TRF-04 | TC-023, TC-025, TC-026, TC-027 |
| REQ-TRF-05 | TC-029, TC-030, TC-031 |
| REQ-TRF-06 | TC-032 |
| REQ-TRF-07 | TC-037, TC-038, TC-039, TC-040 |
| REQ-TRF-08 | TC-036 |
| REQ-TRF-09 | TC-024 |
| REQ-UI-01 | TC-055, TC-056, TC-059 |
| REQ-UI-02 | TC-055, TC-057 |
| REQ-UI-03 | TC-058, TC-059 |

## Авторизация

### TC-001 Регистрация с валидными данными

**Требования:** REQ-AUTH-01, REQ-AUTH-02 · **Приоритет:** high · **Severity:** critical · **Тип:** smoke · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | POST /auth/register {email: new1@example.com, password: Secret123} | 201, в ответе id и email new1@example.com |
| 2 | Войти этим пользователем, GET /accounts | Два счета: RUB и USD, balance "0.00" |

### TC-002 Повторная регистрация с тем же email (в другом регистре)

**Требования:** REQ-AUTH-01 · **Приоритет:** medium · **Severity:** major · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | POST /auth/register {email: ALICE@example.com, password: Secret123} | 409 email already registered |

### TC-003 Регистрация: граничные значения длины пароля

**Требования:** REQ-AUTH-01 · **Приоритет:** medium · **Severity:** normal · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Пароль из 7 символов | 422 |
| 2 | Пароль из 8 символов | 201 |
| 3 | Пароль из 64 символов | 201 |
| 4 | Пароль из 65 символов | 422 |

### TC-004 Регистрация с невалидным email

**Требования:** REQ-AUTH-01 · **Приоритет:** medium · **Severity:** minor · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | email: "alice", "alice@", "@example.com", пустая строка | 422 для каждого значения, пользователь не создан |

### TC-005 Вход с верными данными

**Требования:** REQ-AUTH-03, REQ-AUTH-04 · **Приоритет:** high · **Severity:** critical · **Тип:** smoke · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | POST /auth/login {alice@example.com, Passw0rd!} | 200, access_token, token_type = bearer |
| 2 | Декодировать токен на jwt.io | header alg = HS256; payload содержит sub, iat, exp; exp − iat = 1800 c |

### TC-006 Вход с неверным паролем и с несуществующим email

**Требования:** REQ-AUTH-03 · **Приоритет:** high · **Severity:** major · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Вход alice@example.com с паролем wrong | 401 invalid credentials |
| 2 | Вход nobody@example.com с паролем Passw0rd! | 401 с тем же текстом invalid credentials |

### TC-007 Запрос защищенного эндпоинта без токена и с битым токеном

**Требования:** REQ-AUTH-05 · **Приоритет:** high · **Severity:** critical · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | GET /accounts без заголовка Authorization | 401 |
| 2 | GET /accounts с Authorization: Bearer abc.def.ghi | 401 invalid token |

### TC-008 Блокировка после 5 неудачных попыток входа

**Требования:** REQ-AUTH-06 · **Приоритет:** high · **Severity:** major · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | 5 раз войти как carol с неверным паролем | Каждый раз 401 |
| 2 | Войти как carol с верным паролем | 429 too many failed attempts |
| 3 | Выполнить reset.ps1 (или подождать 5 минут) и войти с верным паролем | 200 |

### TC-009 Успешный вход сбрасывает счетчик неудачных попыток

**Требования:** REQ-AUTH-06 · **Приоритет:** medium · **Severity:** normal · **Тип:** security · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | 4 раза неверный пароль carol | 401 |
| 2 | 1 раз верный пароль | 200 |
| 3 | Еще 4 раза неверный пароль, затем верный | Последний вход 200 (блокировки нет) |

## 2FA

### TC-010 Подключение 2FA: setup + enable верным кодом

**Требования:** REQ-2FA-01 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен bob, POST /auth/2fa/setup | 200, secret и otpauth_uri |
| 2 | Добавить secret в Google Authenticator (или pyotp), POST /auth/2fa/enable {code} | 204 |
| 3 | Вход bob без otp | 401 otp required |

### TC-011 Включение 2FA неверным кодом

**Требования:** REQ-2FA-01 · **Приоритет:** medium · **Severity:** major · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | setup, затем enable с кодом 000000 | 400 invalid otp |
| 2 | Вход bob без otp | 200 — 2FA не включилась |

### TC-012 Вход с включенной 2FA: таблица решений по полю otp

**Требования:** REQ-2FA-02 · **Приоритет:** high · **Severity:** critical · **Тип:** security · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | dave: otp не передан | 401 otp required |
| 2 | dave: otp = верный код из приложения (секрет JBSWY3DPEHPK3PXP) | 200, токен |
| 3 | dave: otp = 123456 (неверный) | 401 invalid otp |
| 4 | dave: otp = "" (пустая строка) | 401 invalid otp |
| 5 | dave: otp = null | 401 otp required |

### TC-013 Неверные коды 2FA учитываются в блокировке входа

**Требования:** REQ-AUTH-06, REQ-2FA-02 · **Приоритет:** medium · **Severity:** major · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | 5 раз войти как dave с верным паролем и неверным otp | 401 invalid otp |
| 2 | Вход dave с верным паролем и верным otp | 429 |

### TC-014 Отключение 2FA только с верным кодом

**Требования:** REQ-2FA-04 · **Приоритет:** medium · **Severity:** major · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен dave, POST /auth/2fa/disable {code: 000000} | 400 |
| 2 | POST /auth/2fa/disable с верным кодом | 204 |
| 3 | Вход dave без otp | 200 |

## Счета

### TC-015 Список счетов текущего пользователя

**Требования:** REQ-ACC-01, REQ-ACC-04 · **Приоритет:** high · **Severity:** critical · **Тип:** smoke · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен alice, GET /accounts | Ровно 2 счета alice: RUB 100000.00 и USD 1000.00; суммы — строки с 2 знаками |

### TC-016 Получение своего счета по id

**Требования:** REQ-ACC-02 · **Приоритет:** medium · **Severity:** normal · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен alice, GET /accounts/3 | 200, currency RUB, balance 100000.00 |

### TC-017 Пополнение счета: валидные и граничные суммы

**Требования:** REQ-ACC-03 · **Приоритет:** medium · **Severity:** normal · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | POST /accounts/3/topup {amount: "0.01"} | 201, баланс +0.01, в истории операция topup |
| 2 | amount: "1000000" | 201 |
| 3 | amount: "0", "-1", "1000000.01", "1.001" | 422 для каждого, баланс не изменился |

### TC-018 Пополнение чужого счета

**Требования:** REQ-ACC-03, REQ-SEC-01 · **Приоритет:** medium · **Severity:** critical · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен alice, POST /accounts/5/topup {amount: 100} | 404, баланс bob не изменился |

## Переводы: комиссия

### TC-019 Перевод RUB→RUB: успешный сценарий

**Требования:** REQ-TRF-01, REQ-TRF-03 · **Приоритет:** high · **Severity:** blocker · **Тип:** smoke · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен alice, POST /transfers {from 3, to 5, amount "5000"} | 201, fee 50.00, amount_to 5000.00, rate null |
| 2 | GET /accounts (alice) и GET /accounts (bob) | alice RUB 94950.00 (−5000 − 50), bob RUB 55000.00 |

### TC-020 Минимальная комиссия 10 ₽: граничные значения

**Требования:** REQ-TRF-03 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 0.01 ₽ | fee 10.00 |
| 2 | Перевод 999.99 ₽ | fee 10.00 |
| 3 | Перевод 1000.00 ₽ | fee 10.00 |
| 4 | Перевод 1000.01 ₽ | fee 10.00 |
| 5 | Перевод 1100.00 ₽ | fee 11.00 |

### TC-021 Максимальная комиссия 500 ₽: граничные значения

**Требования:** REQ-TRF-03 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login); при нехватке средств пополнить счет 3 через topup

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 49999.99 ₽ | fee 500.00 (499.9999 → 500.00) |
| 2 | Перевод 50000.00 ₽ | fee 500.00 |
| 3 | Перевод 50000.01 ₽ | fee 500.00 |
| 4 | Пополнить счет, перевод 75000.00 ₽ | fee 500.00 |

### TC-022 Округление комиссии ROUND_HALF_UP

**Требования:** REQ-TRF-03 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 1234.56 ₽ | fee 12.35 (12.3456) |
| 2 | Перевод 1250.50 ₽ | fee 12.51 (12.505 — половина округляется вверх) |
| 3 | Перевод 1234.40 ₽ | fee 12.34 (12.344) |

### TC-023 Комиссия для USD-счета пересчитывается по курсу

**Требования:** REQ-TRF-03, REQ-TRF-04 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 10.00 USD со счета 4 на счет 6 | fee 0.11 (мин. 10 ₽ / 92.475 = 0.10814 → 0.11) |
| 2 | Перевод 100.00 USD | fee 1.00 (1% от 9247.50 ₽ = 92.475 ₽ → 1.00 $) |
| 3 | Перевод 700.00 USD | fee 5.41 (макс. 500 ₽ / 92.475 = 5.4069 → 5.41) |

### TC-024 Комиссия зачисляется на системный счет

**Требования:** REQ-TRF-09 · **Приоритет:** medium · **Severity:** major · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Запомнить баланс системного RUB-счета: SELECT balance FROM accounts a JOIN users u ON u.id=a.user_id WHERE u.is_system AND currency='RUB' | Значение X |
| 2 | Перевод 5000 ₽ alice → bob | fee 50.00 |
| 3 | Повторить SELECT | X + 50.00 |

## Переводы: конвертация

### TC-025 Перевод USD→RUB с конвертацией

**Требования:** REQ-TRF-04 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 10.00 USD со счета 4 на счет 5 | 201, rate 92.475000, amount_to 924.75, currency_to RUB |
| 2 | Балансы | alice USD 989.89 (−10 −0.11), bob RUB 50924.75 |

### TC-026 Перевод RUB→USD с конвертацией

**Требования:** REQ-TRF-04 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 1000.00 ₽ со счета 3 на счет 6 | amount_to 10.81 (1000 / 92.475 = 10.8137), fee 10.00 ₽ |

### TC-027 Округление при конвертации (третий знак ≥ 5)

**Требования:** REQ-TRF-04 · **Приоритет:** medium · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 10.01 USD на RUB-счет | amount_to 925.67 (925.67475) |
| 2 | Перевод 0.07 USD на RUB-счет | amount_to 6.47 (6.47325) |
| 3 | Перевод 50.00 ₽ на USD-счет | amount_to 0.54 (0.540686) |

### TC-028 Перевод между своими счетами разной валюты

**Требования:** REQ-TRF-01, REQ-HIST-01 · **Приоритет:** medium · **Severity:** normal · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 1000 ₽ со счета 3 на свой USD-счет 4 | 201, amount_to 10.81 |
| 2 | GET /transactions | Операция с direction = self |

## Переводы: лимит и валидация

### TC-029 Суточный лимит: ровно 300 000 ₽ разрешено

**Требования:** REQ-TRF-05 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Пополнить счет 3 на 300000 | 201 |
| 2 | Перевод 300000.00 ₽ на счет 5 | 201 (итог за сутки = лимиту) |
| 3 | Перевод 0.01 ₽ | 422 daily transfer limit exceeded |

### TC-030 Суточный лимит: сумма нескольких переводов

**Требования:** REQ-TRF-05 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Пополнить счет 3 на 300000; перевод 200000 ₽ | 201 |
| 2 | Перевод 100000.01 ₽ | 422, балансы не изменились |
| 3 | Перевод 100000.00 ₽ | 201 |

### TC-031 Лимит учитывает переводы со всех счетов (RUB и USD)

**Требования:** REQ-TRF-05 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Пополнить USD-счет 4 на 3000; перевод 3000 USD (= 277 425 ₽) | 201 |
| 2 | Пополнить счет 3; перевод 30000 ₽ (итого 307 425 ₽) | 422 daily transfer limit exceeded |

### TC-032 Недостаточно средств с учетом комиссии

**Требования:** REQ-TRF-06 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | carol (баланс 0): перевод 1 ₽ | 422 insufficient funds |
| 2 | dave (RUB 10000): перевод 9995 ₽ (нужно 9995 + 99.95) | 422 insufficient funds |
| 3 | dave: перевод 9900 ₽ (нужно 9900 + 99 = 9999) | 201, остаток 1.00 |

### TC-033 Валидация суммы перевода

**Требования:** REQ-TRF-02 · **Приоритет:** medium · **Severity:** major · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | amount: "0", "-100", "0.001", "1000000.01", "abc", пустая строка, null | 422 для каждого |
| 2 | amount: "0.01" и "1000000" (при достаточном балансе/лимите) | 0.01 — 201; 1000000 — 422 из-за лимита, но не из-за валидации |

### TC-034 Перевод на тот же счет и на несуществующий счет

**Требования:** REQ-TRF-01 · **Приоритет:** medium · **Severity:** normal · **Тип:** functional · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | from 3, to 3 | 422 cannot transfer to the same account |
| 2 | from 3, to 99999 | 404 destination account not found |
| 3 | from 3, to 1 (системный счет комиссий) | 404 |

### TC-035 Перевод с чужого счета

**Требования:** REQ-TRF-01, REQ-SEC-01 · **Приоритет:** high · **Severity:** blocker · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен alice, from 5 (счет bob), to 3 | 404 source account not found, балансы не изменились |

### TC-036 Параллельные переводы не уводят баланс в минус

**Требования:** REQ-TRF-08, REQ-DATA-02 · **Приоритет:** medium · **Severity:** critical · **Тип:** functional · **Поведение:** destructive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | dave (RUB 10000): одновременно отправить 5 запросов перевода по 3000 ₽ (Postman Runner / скрипт) | Успешны не больше 3, остальные 422 insufficient funds |
| 2 | GET /accounts dave | Баланс ≥ 0 и равен 10000 − успешные × 3030 |

## Внешние сервисы

### TC-037 Отказ антифрода

**Требования:** REQ-TRF-07 · **Приоритет:** high · **Severity:** critical · **Тип:** integration · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 77777.00 ₽ (стаб WireMock: deny) | 403 transfer rejected by antifraud |
| 2 | Балансы и история | Без изменений |

### TC-038 Таймаут антифрода

**Требования:** REQ-TRF-07 · **Приоритет:** medium · **Severity:** major · **Тип:** integration · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Перевод 66666.00 ₽ (стаб: задержка 5 c, таймаут клиента 2 c) | 503 antifraud service timeout примерно через 2 c |
| 2 | Балансы | Без изменений |

### TC-039 Сервис курсов недоступен

**Требования:** REQ-TRF-07 · **Приоритет:** medium · **Severity:** major · **Тип:** integration · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Через WireMock admin (POST /__admin/mappings) добавить стаб GET /rates/USD/RUB → 500 с priority 1 | 201 |
| 2 | Перевод USD→RUB | 503 rates service unavailable |
| 3 | Перевод RUB→RUB | 201 — курс не нужен |
| 4 | POST /__admin/reset | Стабы восстановлены |

### TC-040 Сервис курсов вернул некорректный курс

**Требования:** REQ-TRF-07 · **Приоритет:** medium · **Severity:** major · **Тип:** integration · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Стаб: {"rate": "abc"}, затем {"rate": "0"}, затем {"rate": "-1"}, затем ответ без поля rate | Перевод USD→RUB → 503 в каждом случае, балансы без изменений |

## История и уведомления

### TC-041 История операций: состав, порядок, direction

**Требования:** REQ-HIST-01 · **Приоритет:** medium · **Severity:** major · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | alice: перевод bob 100 ₽; bob: перевод alice 50 ₽ | 201, 201 |
| 2 | GET /transactions (alice) | Сверху входящая 50 (direction in), затем исходящая 100 (out), затем topup; чужих операций нет |

### TC-042 Пагинация истории

**Требования:** REQ-HIST-01 · **Приоритет:** medium · **Severity:** minor · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Сделать 5 переводов; GET /transactions?limit=2&offset=0, затем offset=2 | По 2 записи, без пересечений |
| 2 | limit=0, limit=201, offset=-1 | 422 |

### TC-043 Уведомления отправителю и получателю

**Требования:** REQ-HIST-02 · **Приоритет:** high · **Severity:** major · **Тип:** integration · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | alice: перевод 1000 ₽ на счет bob | 201 |
| 2 | Через 3 c GET /notifications (alice) | Сообщение «Перевод 1000.00 RUB на счет #5 выполнен. Комиссия 10.00 RUB» |
| 3 | GET /notifications (bob) | Сообщение «Поступление 1000.00 RUB со счета #3» |

## Kafka

### TC-044 Событие перевода публикуется ровно один раз

**Требования:** REQ-EVT-01 · **Приоритет:** high · **Severity:** critical · **Тип:** integration · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить перевод RUB→RUB и перевод RUB→USD, запомнить tx_id | 201 |
| 2 | Redpanda Console → Topics → transactions → найти сообщения по key = tx_id | Для каждого tx_id ровно 1 сообщение |

### TC-045 Событие соответствует схеме и данным операции

**Требования:** REQ-EVT-02 · **Приоритет:** high · **Severity:** critical · **Тип:** integration · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Взять сообщение перевода USD→RUB из топика | Валидно по transaction_event.schema.json: все поля, суммы — строки с 2 знаками |
| 2 | Сравнить с ответом API и строкой в transactions (БД) | amount, fee, amount_to, currency, rate совпадают; заголовок request_id = X-Request-ID ответа |

### TC-046 Невалидный JSON уходит в DLQ

**Требования:** REQ-EVT-04 · **Приоритет:** medium · **Severity:** major · **Тип:** integration · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Redpanda Console → transactions → Produce: значение «not a json» | Сообщение отправлено |
| 2 | Открыть топик transactions.dlq | Появилось сообщение «not a json» с заголовком error |
| 3 | Сделать обычный перевод | Уведомление пришло — notifier не завис |

### TC-047 Сообщение не по схеме уходит в DLQ

**Требования:** REQ-EVT-04 · **Приоритет:** medium · **Severity:** major · **Тип:** integration · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Produce в transactions: {"event_id": "x"} | Сообщение в transactions.dlq, заголовок error содержит описание нарушения схемы |

### TC-048 Повтор события не создает дублей уведомлений

**Требования:** REQ-EVT-03 · **Приоритет:** medium · **Severity:** major · **Тип:** integration · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Скопировать значение события перевода из топика и отправить его в transactions повторно | Сообщение отправлено |
| 2 | SELECT count(*) FROM notifications WHERE event_id = '<event_id>' | 2 (debit + credit), а не 4 |

## Данные (БД)

### TC-049 Балансы сходятся с историей операций

**Требования:** REQ-DATA-01 · **Приоритет:** high · **Severity:** critical · **Тип:** integration · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Выполнить переводы RUB→RUB, USD→RUB, RUB→USD | 201 |
| 2 | SQL с CTE: для каждого счета balance = Σ зачислений (amount_to) + Σ комиссий на счет − Σ списаний (amount + fee) | Расхождений нет (0 строк) |

### TC-050 Нет отрицательных балансов и денег в float

**Требования:** REQ-DATA-02, REQ-DATA-03 · **Приоритет:** medium · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | SELECT * FROM accounts WHERE balance < 0 | 0 строк |
| 2 | SELECT column_name, data_type FROM information_schema.columns WHERE table_name IN ('accounts','transactions') AND column_name IN ('balance','amount','fee','amount_to') | Везде numeric |

## Безопасность

### TC-051 IDOR: чтение чужого счета по id

**Требования:** REQ-ACC-02, REQ-SEC-01 · **Приоритет:** high · **Severity:** critical · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1; получен токен alice@example.com (POST /auth/login)

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Токен alice, GET /accounts/5 (счет bob) | 404 account not found, баланс bob не раскрыт |
| 2 | GET /accounts/99999 | 404 с тем же текстом |

### TC-052 JWT: истекший токен и токен с измененной подписью/payload

**Требования:** REQ-AUTH-04 · **Приоритет:** high · **Severity:** critical · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Сгенерировать токен с exp в прошлом, подписанный тем же секретом (jwt.io, секрет dev-secret-change-me) | GET /auth/me → 401 |
| 2 | Взять валидный токен alice, поменять sub на 3 в payload, подпись не трогать | 401 |
| 3 | Подписать токен другим секретом | 401 |

### TC-053 JWT: alg = none

**Требования:** REQ-AUTH-04 · **Приоритет:** high · **Severity:** critical · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Собрать токен header {"alg":"none","typ":"JWT"}, payload {"sub":"2","exp":9999999999}, пустая подпись (base64url, «xxx.yyy.») | GET /auth/me → 401 |

### TC-054 CORS: чужой Origin

**Требования:** REQ-SEC-02 · **Приоритет:** high · **Severity:** major · **Тип:** security · **Поведение:** negative

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | curl -i http://localhost:8000/health -H "Origin: https://evil.example" | Нет заголовка Access-Control-Allow-Origin |
| 2 | То же с Origin: http://localhost:8090 | Access-Control-Allow-Origin: http://localhost:8090 |
| 3 | Preflight: OPTIONS /transfers с Origin evil + Access-Control-Request-Method: POST | Не разрешено (400 / без ACAO) |

## UI

### TC-055 Вход через веб-интерфейс и отображение данных

**Требования:** REQ-UI-01, REQ-UI-02 · **Приоритет:** high · **Severity:** critical · **Тип:** smoke · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Открыть http://localhost:8090, войти alice@example.com / Passw0rd! | Видны email в шапке, 2 счета с балансами, история, уведомления |
| 2 | Выйти, войти с неверным паролем | Сообщение «Неверный email или пароль» |

### TC-056 Вход с 2FA через веб-интерфейс

**Требования:** REQ-UI-01, REQ-2FA-02 · **Приоритет:** high · **Severity:** critical · **Тип:** functional · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Ввести dave@example.com / Passw0rd!, нажать «Войти» | Появилось поле «Код из приложения 2FA» и подсказка |
| 2 | Ввести неверный код | «Неверный код» |
| 3 | Ввести верный код | Открылся кабинет dave |

### TC-057 Перевод через веб-интерфейс

**Требования:** REQ-UI-02, REQ-HIST-02 · **Приоритет:** high · **Severity:** critical · **Тип:** smoke · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | alice: со счета №3 на счет 5, сумма 1234,56 (с запятой) | «Готово: 1 234.56 ₽, комиссия 12.35 ₽» |
| 2 | Посмотреть счета и историю | Баланс RUB уменьшился на 1246.91, сверху новая операция |
| 3 | Подождать 2 c | Появилось уведомление о переводе |
| 4 | Перевод суммы больше баланса | Красное сообщение об ошибке, балансы не изменились |

### TC-060 Сквозной request_id: поиск запроса в логах

**Требования:** REQ-NFR-01 · **Приоритет:** medium · **Severity:** minor · **Тип:** other · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | В DevTools → Network взять X-Request-ID ответа POST /transfers | Заголовок есть |
| 2 | Dozzle (http://localhost:8888) → поиск по этому id | Строки api (request, transfer completed, event delivered) и notifier (notifications saved) с этим request_id |

## UI: мобильная версия

### TC-058 Мобильная верстка: iPhone 13 (390×844) и Pixel 7 (412×915)

**Требования:** REQ-UI-03 · **Приоритет:** high · **Severity:** major · **Тип:** compatibility · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | DevTools → Device Toolbar → iPhone 13, войти alice | Нет горизонтальной прокрутки страницы |
| 2 | Форма перевода | Поля и кнопка «Перевести» помещаются по ширине, кнопка во всю ширину |
| 3 | История | Суммы и комиссии видны полностью |
| 4 | Повторить для Pixel 7 и для ширины 360 px | То же |

### TC-059 Мобильная версия: перевод и вход с 2FA

**Требования:** REQ-UI-01, REQ-UI-03 · **Приоритет:** medium · **Severity:** major · **Тип:** compatibility · **Поведение:** positive

**Предусловия:** Стенд поднят, выполнен .\infra\reset.ps1

| # | Шаг | Ожидаемый результат |
|---|---|---|
| 1 | Эмуляция iPhone 13: вход dave с 2FA | Поле кода видно, клавиатура цифровая (inputmode=numeric) |
| 2 | Перевод 100 ₽ на счет 3 | Результат перевода виден без горизонтальной прокрутки |
