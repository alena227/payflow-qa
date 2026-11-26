package qa.payflow;

import io.qameta.allure.Feature;
import io.restassured.response.Response;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import qa.payflow.support.ApiClient;
import qa.payflow.support.Money;

import java.math.BigDecimal;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Комиссия за перевод. Аналог tests/api/test_transfer_fee.py.
 *
 * @ParameterizedTest + @ValueSource/@CsvSource = параметризация (как @pytest.mark.parametrize).
 * Ожидаемую комиссию берём из оракула Money.expectedFee, а не из кода приложения.
 */
@Feature("Переводы: комиссия")
class TransferFeeTest {

    private final ApiClient recipient = ApiClient.newUser("0", "0");

    @ParameterizedTest(name = "комиссия RUB для суммы {0}")
    @ValueSource(strings = {"0.01", "999.99", "1000.00", "1000.01", "1100.00",
                            "1234.56", "1250.50", "49999.99", "50000.00", "75000.00"})
    @DisplayName("Комиссия RUB совпадает с расчётом по требованиям")
    void feeRub(String amount) {
        ApiClient user = ApiClient.newUser("100000", "0");
        Map<String, Integer> acc = user.accountIds();
        Response r = user.transfer(acc.get("RUB"), recipient.accountIds().get("RUB"), amount);

        assertEquals(201, r.statusCode(), r.asString());
        assertEquals(Money.expectedFee(amount, "RUB"),
                new BigDecimal(r.jsonPath().getString("fee")));
    }

    @ParameterizedTest(name = "комиссия USD для суммы {0}")
    @ValueSource(strings = {"10.00", "100.00", "700.00"})
    @DisplayName("Комиссия USD пересчитывается по курсу")
    void feeUsd(String amount) {
        ApiClient user = ApiClient.newUser("0", "1000");
        Map<String, Integer> acc = user.accountIds();
        Response r = user.transfer(acc.get("USD"), recipient.accountIds().get("USD"), amount);

        assertEquals(201, r.statusCode(), r.asString());
        assertEquals(Money.expectedFee(amount, "USD"),
                new BigDecimal(r.jsonPath().getString("fee")));
    }

    @ParameterizedTest(name = "конвертация {0} {1} -> {2}")
    @CsvSource({
            "10.01, USD, RUB",
            "0.07,  USD, RUB",
            "1000.00, RUB, USD",
            "50.00, RUB, USD",
    })
    @DisplayName("Конвертация даёт сумму по курсу с правильным округлением")
    void conversion(String amount, String from, String to) {
        ApiClient user = ApiClient.newUser("10000", "1000");
        Map<String, Integer> acc = user.accountIds();
        Map<String, Integer> rec = recipient.accountIds();
        Response r = user.transfer(acc.get(from), rec.get(to), amount);

        assertEquals(201, r.statusCode(), r.asString());
        assertEquals(Money.expectedAmountTo(amount, from, to),
                new BigDecimal(r.jsonPath().getString("amount_to")));
    }

    @DisplayName("Перевод RUB->RUB: балансы меняются на сумму + комиссию")
    @org.junit.jupiter.api.Test
    void happyPathBalances() {
        ApiClient user = ApiClient.newUser("100000", "0");
        Map<String, Integer> acc = user.accountIds();
        Response r = user.transfer(acc.get("RUB"), recipient.accountIds().get("RUB"), "5000");

        assertEquals(201, r.statusCode());
        assertEquals("50.00", r.jsonPath().getString("fee"));
        assertEquals(new BigDecimal("94950.00"), new BigDecimal(user.balance("RUB")));
    }
}
