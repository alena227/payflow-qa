package qa.payflow;

import io.qameta.allure.Feature;
import io.restassured.response.Response;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import qa.payflow.support.ApiClient;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Суточный лимит и нехватка средств. Аналог tests/api/test_transfer_limits.py.
 */
@Feature("Переводы: лимит и валидация")
class TransferLimitTest {

    private final ApiClient recipient = ApiClient.newUser("0", "0");
    private int recRub() { return recipient.accountIds().get("RUB"); }

    @Test
    @DisplayName("Перевод ровно на суточный лимит 300000 разрешён, следующая копейка - нет")
    void exactDailyLimit() {
        ApiClient user = ApiClient.newUser("400000", "0");
        int rub = user.accountIds().get("RUB");

        assertEquals(201, user.transfer(rub, recRub(), "300000.00").statusCode());
        Response over = user.transfer(rub, recRub(), "0.01");
        assertEquals(422, over.statusCode());
        assertEquals("daily transfer limit exceeded", over.jsonPath().getString("detail"));
    }

    @Test
    @DisplayName("Недостаточно средств с учётом комиссии -> 422, баланс не меняется")
    void insufficientFunds() {
        ApiClient user = ApiClient.newUser("10000", "0");
        int rub = user.accountIds().get("RUB");
        // нужно 9995 + 99.95 = 10094.95, на счёте 10000
        Response r = user.transfer(rub, recRub(), "9995");
        assertEquals(422, r.statusCode());
        assertEquals("insufficient funds", r.jsonPath().getString("detail"));
        assertEquals("10000.00", user.balance("RUB"));
    }

    @Test
    @DisplayName("Перевод на тот же счёт -> 422")
    void sameAccount() {
        ApiClient user = ApiClient.newUser("1000", "0");
        int rub = user.accountIds().get("RUB");
        Response r = user.transfer(rub, rub, "10");
        assertEquals(422, r.statusCode());
        assertEquals("cannot transfer to the same account", r.jsonPath().getString("detail"));
    }

    @Test
    @DisplayName("Перевод с чужого счёта -> 404")
    void foreignSourceAccount() {
        ApiClient user = ApiClient.newUser("1000", "0");
        // пытаемся списать со счёта recipient
        Response r = user.transfer(recRub(), user.accountIds().get("RUB"), "10");
        assertEquals(404, r.statusCode());
        assertEquals("source account not found", r.jsonPath().getString("detail"));
    }
}
