package qa.payflow.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;

import java.util.Map;
import java.util.UUID;

import static io.restassured.RestAssured.given;

/**
 * Обёртка над Rest Assured — аналог helpers/api.py.
 *
 * Rest Assured пишется в стиле given().when().then(): задать запрос -> отправить -> проверить.
 * Здесь методы просто возвращают Response, а проверки (assert) делают сами тесты.
 */
public class ApiClient {
    private static final ObjectMapper JSON = new ObjectMapper();
    private String token;

    private RequestSpecification base() {
        RequestSpecification spec = given().baseUri(Config.API_URL).contentType("application/json");
        if (token != null) spec.header("Authorization", "Bearer " + token);
        return spec;
    }

    // ---------- аутентификация ----------
    public Response register(String email, String password) {
        return base().body(Map.of("email", email, "password", password)).post("/auth/register");
    }

    public Response login(String email, String password) {
        Response r = base().body(Map.of("email", email, "password", password)).post("/auth/login");
        if (r.statusCode() == 200) token = r.jsonPath().getString("access_token");
        return r;
    }

    public Response loginWithOtp(String email, String password, String otp) {
        Response r = base().body(Map.of("email", email, "password", password, "otp", otp)).post("/auth/login");
        if (r.statusCode() == 200) token = r.jsonPath().getString("access_token");
        return r;
    }

    public void setToken(String token) { this.token = token; }

    // ---------- счета и переводы ----------
    public Response accounts() { return base().get("/accounts"); }

    public Response topup(int accountId, String amount) {
        return base().body(Map.of("amount", amount)).post("/accounts/" + accountId + "/topup");
    }

    public Response transfer(int fromId, int toId, String amount) {
        return base().body(Map.of("from_account_id", fromId, "to_account_id", toId, "amount", amount))
                .post("/transfers");
    }

    public Response enable2fa(String code) {
        return base().body(Map.of("code", code)).post("/auth/2fa/enable");
    }

    public Response setup2fa() { return base().post("/auth/2fa/setup"); }

    // ---------- вспомогательное ----------
    /** Создать пользователя с уникальным email, залогинить, при необходимости пополнить счета. */
    public static ApiClient newUser(String rub, String usd) {
        ApiClient c = new ApiClient();
        String email = "java-" + UUID.randomUUID().toString().substring(0, 12) + "@example.com";
        c.register(email, Config.PASSWORD);
        c.login(email, Config.PASSWORD);
        Map<String, Integer> acc = c.accountIds();
        topupIfNeeded(c, acc.get("RUB"), rub);
        topupIfNeeded(c, acc.get("USD"), usd);
        return c;
    }

    private static void topupIfNeeded(ApiClient c, int accountId, String amount) {
        if (new java.math.BigDecimal(amount).signum() > 0) {
            c.topup(accountId, amount);
        }
    }

    /** {"RUB": 3, "USD": 4} — номера счетов текущего пользователя. */
    public Map<String, Integer> accountIds() {
        Response r = accounts();
        return r.jsonPath().getList("currency", String.class).stream()
                .collect(java.util.stream.Collectors.toMap(
                        cur -> cur,
                        cur -> r.jsonPath().getInt("find { it.currency == '" + cur + "' }.id")));
    }

    public String balance(String currency) {
        return accounts().jsonPath().getString("find { it.currency == '" + currency + "' }.balance");
    }

    public static JsonNode parse(String body) {
        try {
            return JSON.readTree(body);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
