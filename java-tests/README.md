# Java-автотесты PayFlow (JUnit 5, Rest Assured, Cucumber, Allure)

Модуль API-автотестов на Java 17 — тот же набор проверок, что в Python-тестах, но на стеке из банковских вакансий.

## Запуск
Нужны Java 17 и Maven (проверка: `java -version`, `mvn -version`). Стенд должен быть поднят (`docker compose up -d`).

```powershell
cd java-tests
mvn test                                  # все тесты
mvn test -Dtest=TransferFeeTest           # один класс
mvn test -Dpayflow.api=http://localhost:8000   # другой адрес API
```

## Структура
```
pom.xml                                настройки проекта и список библиотек (аналог requirements.txt)
src/test/java/qa/payflow/
  support/
    Config.java        адрес API, пароль, курс
    ApiClient.java     обёртка над Rest Assured (аналог helpers/api.py)
    Money.java         оракул комиссии и конвертации на BigDecimal (аналог helpers/money.py)
    Totp.java          генерация кода 2FA (аналог pyotp)
  AuthTest.java            регистрация, вход, токен
  TransferFeeTest.java     комиссия, конвертация (параметризованные тесты)
  TransferLimitTest.java   суточный лимит, нехватка средств, чужой счёт
  TwoFactorTest.java       таблица решений по коду 2FA
  RunCucumberTest.java     запускает .feature-сценарии
  steps/                   шаги Cucumber (связывают Gherkin с кодом)
src/test/resources/features/
  transfers.feature        BDD: перевод, превышение лимита
  login_2fa.feature        BDD: вход с 2FA
```

## Java глазами питониста
| Python (pytest) | Java (JUnit 5) |
|---|---|
| `def test_x():` | `@Test void testX()` |
| `assert a == b` | `assertEquals(b, a)` (ожидаемое первым) |
| `@pytest.mark.parametrize` | `@ParameterizedTest` + `@ValueSource` / `@CsvSource` |
| `Decimal` | `BigDecimal` |
| `requests` | Rest Assured: `given().body(...).post(...)` |
| динамические типы | статические: `String email`, тип пишется явно |

## Cucumber (BDD)
Сценарии написаны на Gherkin (`Дано / Когда / Тогда`) по-русски — их понимает и не-программист. Каждая фраза сценария связана с Java-методом в `steps/` через аннотацию (`@Дано`, `@Когда`, `@Тогда`).

## Allure-отчёт
После прогона:
```powershell
mvn test
# результаты в target/allure-results; для HTML-отчёта нужен Allure CLI (день 12)
```
