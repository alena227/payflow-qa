package qa.payflow.support;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Тестовый оракул комиссии — то же, что helpers/money.py в Python-тестах.
 * Считаем ожидаемую комиссию ПО ТРЕБОВАНИЯМ, а не копируем из кода приложения.
 *
 * Отличие от Python: деньги в Java считаем через BigDecimal (аналог Decimal).
 * double использовать нельзя — он теряет точность на деньгах.
 */
public final class Money {
    private Money() {}

    private static final BigDecimal RATE = new BigDecimal(Config.RATE);
    private static final BigDecimal FEE_RATE = new BigDecimal("0.01");
    private static final BigDecimal FEE_MIN_RUB = new BigDecimal("10");
    private static final BigDecimal FEE_MAX_RUB = new BigDecimal("500");

    /** Округление до копеек по ROUND_HALF_UP (0.005 -> 0.01). */
    private static BigDecimal round(BigDecimal x) {
        return x.setScale(2, RoundingMode.HALF_UP);
    }

    private static BigDecimal toRub(BigDecimal amount, String currency) {
        return currency.equals("RUB") ? amount : amount.multiply(RATE);
    }

    /** Ожидаемая комиссия: 1% в рублях, но не меньше 10 и не больше 500 ₽, в валюте счёта. */
    public static BigDecimal expectedFee(String amount, String currency) {
        BigDecimal amountRub = toRub(new BigDecimal(amount), currency);
        BigDecimal feeRub = amountRub.multiply(FEE_RATE);
        if (feeRub.compareTo(FEE_MIN_RUB) < 0) feeRub = FEE_MIN_RUB;
        if (feeRub.compareTo(FEE_MAX_RUB) > 0) feeRub = FEE_MAX_RUB;
        BigDecimal fee = currency.equals("RUB") ? feeRub : feeRub.divide(RATE, 10, RoundingMode.HALF_UP);
        return round(fee);
    }

    /** Ожидаемая сумма к зачислению после конвертации. */
    public static BigDecimal expectedAmountTo(String amount, String from, String to) {
        BigDecimal a = new BigDecimal(amount);
        if (from.equals(to)) return a.setScale(2, RoundingMode.HALF_UP);
        if (from.equals("USD")) return round(a.multiply(RATE));
        return round(a.divide(RATE, 10, RoundingMode.HALF_UP));
    }
}
