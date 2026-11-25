# Автотесты PayFlow (Python, pytest)

## Запуск
Один раз, из корня проекта:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tests\requirements.txt
```
Стенд должен быть поднят (`docker compose up -d`). Дальше:
```powershell
.\.venv\Scripts\python.exe -m pytest                       # все тесты
.\.venv\Scripts\python.exe -m pytest tests\api\test_transfer_fee.py   # один файл
.\.venv\Scripts\python.exe -m pytest -k "fee_rub"          # по имени
.\.venv\Scripts\python.exe -m pytest -m money              # по маркеру (smoke, money, security)
.\.venv\Scripts\python.exe -m pytest -x -v                 # подробно и остановиться на первом падении
```
Если активировать окружение (`.\.venv\Scripts\Activate.ps1`), можно писать просто `pytest`.

## Устройство
```
pytest.ini              настройки: где тесты, маркеры
tests/
  conftest.py           фикстуры: user, make_user, recipient, anon
  helpers/api.py        ApiClient — обертка над requests
  helpers/money.py      оракул: ожидаемая комиссия и конвертация по требованиям
  api/
    test_auth.py                  регистрация, вход, JWT, блокировка    (TC-001..009)
    test_2fa.py                   2FA, таблица решений по otp            (TC-010..014)
    test_accounts.py              счета, пополнение                      (TC-015..018)
    test_transfer_fee.py          комиссия, граничные значения           (TC-019..024)
    test_transfer_conversion.py   конвертация RUB<->USD                  (TC-025..028)
    test_transfer_limits.py       суточный лимит, нехватка средств       (TC-029..032)
    test_transfer_validation.py   валидация, чужие счета                 (TC-033..035)
    test_history.py               история, пагинация                     (TC-041, 042)
```

## Принципы
- **Независимость.** Каждый тест создает своего пользователя с уникальным email, поэтому порядок запуска и `reset.ps1` не важны.
- **Оракул отдельно от приложения.** Ожидаемые суммы считаются в `helpers/money.py` по требованиям, а не копируются из кода api.
- **Проверяем последствия, а не только ответ:** после перевода сверяем балансы.
- **Обертка ничего не проверяет за тест**: `ApiClient` возвращает `Response`, все `assert` находятся в тестах.
- Версии зависимостей зафиксированы в `requirements.txt`.

## Результат
| Сборка | Результат |
|---|---|
| `BUGS=0` | 84 passed |
| `BUGS=1` | 11 failed, 73 passed |
