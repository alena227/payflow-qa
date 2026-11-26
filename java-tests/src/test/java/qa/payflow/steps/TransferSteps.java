package qa.payflow.steps;

import io.cucumber.java.ru.Дано;
import io.cucumber.java.ru.Когда;
import io.cucumber.java.ru.Тогда;
import io.restassured.response.Response;
import qa.payflow.support.ApiClient;

import java.math.BigDecimal;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Шаги Cucumber для transfers.feature.
 * Каждая аннотация (@Дано/@Когда/@Тогда) привязывает фразу из сценария к методу.
 * Состояние между шагами храним в полях класса.
 */
public class TransferSteps {

    private ApiClient user;
    private ApiClient recipient;
    private Response lastResponse;

    @Дано("зарегистрирован пользователь с балансом {int} рублей")
    public void userWithBalance(int rub) {
        user = ApiClient.newUser(String.valueOf(rub), "0");
    }

    @Дано("зарегистрирован получатель")
    public void recipient() {
        recipient = ApiClient.newUser("0", "0");
    }

    @Дано("баланс отправителя пополнен до {int} рублей")
    public void topupTo(int target) {
        int rub = user.accountIds().get("RUB");
        BigDecimal current = new BigDecimal(user.balance("RUB"));
        BigDecimal diff = new BigDecimal(target).subtract(current);
        if (diff.signum() > 0) user.topup(rub, diff.toPlainString());
    }

    @Когда("пользователь переводит получателю {int} рублей")
    public void transfer(int amount) {
        Map<String, Integer> acc = user.accountIds();
        lastResponse = user.transfer(acc.get("RUB"), recipient.accountIds().get("RUB"), String.valueOf(amount));
    }

    @Тогда("перевод успешен")
    public void transferOk() {
        assertEquals(201, lastResponse.statusCode(), lastResponse.asString());
    }

    @Тогда("комиссия равна {string}")
    public void feeIs(String fee) {
        assertEquals(fee, lastResponse.jsonPath().getString("fee"));
    }

    @Тогда("баланс отправителя равен {string}")
    public void senderBalanceIs(String balance) {
        assertEquals(balance, user.balance("RUB"));
    }

    @Тогда("перевод отклонён с ошибкой {string}")
    public void transferRejected(String detail) {
        assertEquals(422, lastResponse.statusCode());
        assertEquals(detail, lastResponse.jsonPath().getString("detail"));
    }
}
