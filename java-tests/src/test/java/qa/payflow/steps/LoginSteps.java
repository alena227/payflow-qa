package qa.payflow.steps;

import io.cucumber.java.ru.Дано;
import io.cucumber.java.ru.Когда;
import io.cucumber.java.ru.Тогда;
import io.restassured.response.Response;
import qa.payflow.support.ApiClient;
import qa.payflow.support.Config;
import qa.payflow.support.Totp;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** Шаги Cucumber для login_2fa.feature. */
public class LoginSteps {

    private String email;
    private String secret;
    private Response lastResponse;

    @Дано("зарегистрирован пользователь с включённой 2FA")
    public void userWith2fa() {
        ApiClient c = new ApiClient();
        email = "java-bdd-" + UUID.randomUUID().toString().substring(0, 8) + "@example.com";
        c.register(email, Config.PASSWORD);
        c.login(email, Config.PASSWORD);
        secret = c.setup2fa().jsonPath().getString("secret");
        c.enable2fa(Totp.now(secret));
    }

    @Когда("пользователь входит без кода 2FA")
    public void loginWithoutOtp() {
        lastResponse = new ApiClient().login(email, Config.PASSWORD);
    }

    @Когда("пользователь входит с верным кодом 2FA")
    public void loginWithOtp() {
        lastResponse = new ApiClient().loginWithOtp(email, Config.PASSWORD, Totp.now(secret));
    }

    @Тогда("вход отклонён с сообщением {string}")
    public void loginRejected(String detail) {
        assertEquals(401, lastResponse.statusCode());
        assertEquals(detail, lastResponse.jsonPath().getString("detail"));
    }

    @Тогда("вход успешен")
    public void loginOk() {
        assertEquals(200, lastResponse.statusCode());
    }
}
