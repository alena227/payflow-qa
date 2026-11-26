package qa.payflow.support;

/**
 * Настройки стенда. В Java нет глобальных переменных как в Python —
 * константы живут в классе и читаются через Config.API_URL.
 */
public final class Config {
    private Config() {}

    // Адрес API; можно переопределить флагом: mvn test -Dpayflow.api=http://host:8000
    public static final String API_URL =
            System.getProperty("payflow.api", "http://localhost:8000");

    public static final String PASSWORD = "Secret123!";
    public static final String RATE = "92.4750"; // тот же курс, что в WireMock
}
