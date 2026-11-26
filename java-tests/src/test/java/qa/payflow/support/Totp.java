package qa.payflow.support;

import dev.samstevens.totp.code.DefaultCodeGenerator;
import dev.samstevens.totp.code.HashingAlgorithm;
import dev.samstevens.totp.time.SystemTimeProvider;

/**
 * Генерация 6-значного кода 2FA по секрету — то же, что pyotp.TOTP(secret).now() в Python.
 */
public final class Totp {
    private Totp() {}

    private static final DefaultCodeGenerator GEN = new DefaultCodeGenerator(HashingAlgorithm.SHA1, 6);
    private static final SystemTimeProvider TIME = new SystemTimeProvider();

    public static String now(String secret) {
        try {
            long bucket = Math.floorDiv(TIME.getTime(), 30L);
            return GEN.generate(secret, bucket);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
