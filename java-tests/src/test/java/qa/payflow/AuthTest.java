package qa.payflow;

import io.qameta.allure.Feature;
import io.restassured.response.Response;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import qa.payflow.support.ApiClient;
import qa.payflow.support.Config;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Авторизация и регистрация. Аналог tests/api/test_auth.py.
 *
 * Отличия от pytest:
 * - класс с методами @Test вместо функций def test_...;
 * - assertEquals(ожидаемое, фактическое) вместо assert a == b;
 * - @DisplayName задаёт читаемое имя теста в отчёте.
 */
@Feature("Авторизация")
class AuthTest {

    private String uniqueEmail() {
        return "java-" + UUID.randomUUID().toString().substring(0, 12) + "@example.com";
    }

    @Test
    @DisplayName("Регистрация создаёт пользователя и два пустых счёта")
    void registerCreatesTwoAccounts() {
        ApiClient c = new ApiClient();
        String email = uniqueEmail();

        Response reg = c.register(email, Config.PASSWORD);
        assertEquals(201, reg.statusCode());
        assertEquals(email, reg.jsonPath().getString("email"));

        c.login(email, Config.PASSWORD);
        Response accounts = c.accounts();
        assertEquals(2, accounts.jsonPath().getList("$").size());
        // оба счёта пустые
        accounts.jsonPath().getList("balance", String.class)
                .forEach(b -> assertEquals("0.00", b));
    }

    @Test
    @DisplayName("Повторная регистрация того же email (в другом регистре) -> 409")
    void duplicateEmailRejected() {
        ApiClient c = new ApiClient();
        String email = uniqueEmail();
        assertEquals(201, c.register(email, Config.PASSWORD).statusCode());

        Response dup = c.register(email.toUpperCase(), Config.PASSWORD);
        assertEquals(409, dup.statusCode());
        assertEquals("email already registered", dup.jsonPath().getString("detail"));
    }

    @Test
    @DisplayName("Вход с верными данными возвращает bearer-токен")
    void loginReturnsToken() {
        ApiClient c = ApiClient.newUser("0", "0");
        // newUser уже залогинил; проверим, что логин как таковой работает
        ApiClient fresh = new ApiClient();
        String email = uniqueEmail();
        fresh.register(email, Config.PASSWORD);
        Response login = fresh.login(email, Config.PASSWORD);
        assertEquals(200, login.statusCode());
        assertEquals("bearer", login.jsonPath().getString("token_type"));
        assertNotNull(login.jsonPath().getString("access_token"));
    }

    @Test
    @DisplayName("Неверный пароль -> 401 с общим текстом")
    void wrongPasswordRejected() {
        ApiClient c = new ApiClient();
        String email = uniqueEmail();
        c.register(email, Config.PASSWORD);
        Response r = c.login(email, "wrong-password");
        assertEquals(401, r.statusCode());
        assertEquals("invalid credentials", r.jsonPath().getString("detail"));
    }

    @Test
    @DisplayName("Запрос без токена -> 401")
    void noTokenRejected() {
        Response r = new ApiClient().accounts();
        assertEquals(401, r.statusCode());
    }
}
