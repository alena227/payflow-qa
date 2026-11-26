package qa.payflow;

import io.qameta.allure.Feature;
import io.restassured.response.Response;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import qa.payflow.support.ApiClient;
import qa.payflow.support.Config;
import qa.payflow.support.Totp;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Двухфакторная аутентификация. Аналог части tests/api/test_2fa.py.
 */
@Feature("2FA")
class TwoFactorTest {

    @Test
    @DisplayName("Таблица решений по коду 2FA: нет/неверный/верный")
    void otpDecisionTable() {
        ApiClient c = new ApiClient();
        String email = "java-2fa-" + java.util.UUID.randomUUID().toString().substring(0, 8) + "@example.com";
        c.register(email, Config.PASSWORD);
        c.login(email, Config.PASSWORD);
        String secret = c.setup2fa().jsonPath().getString("secret");
        c.enable2fa(Totp.now(secret));

        // нет кода -> 401 otp required
        Response noOtp = new ApiClient().login(email, Config.PASSWORD);
        assertEquals(401, noOtp.statusCode());
        assertEquals("otp required", noOtp.jsonPath().getString("detail"));

        // неверный код -> 401 invalid otp
        Response wrong = new ApiClient().loginWithOtp(email, Config.PASSWORD, "000000");
        assertEquals(401, wrong.statusCode());
        assertEquals("invalid otp", wrong.jsonPath().getString("detail"));

        // верный код -> 200
        Response ok = new ApiClient().loginWithOtp(email, Config.PASSWORD, Totp.now(secret));
        assertEquals(200, ok.statusCode());
    }
}
