"""UI на мобильных экранах. Требование REQ-UI-03; тест-кейсы TC-058, TC-059.

Эмуляция устройства: задаём размер экрана через viewport. Проверяем два правила вёрстки:
1. нет горизонтальной прокрутки всей страницы (ширина содержимого не больше ширины экрана);
2. ключевые элементы (кнопка «Перевести», суммы в истории) видны целиком, а не обрезаны.

Параметризуем по устройствам, чтобы один тест проверил и iPhone, и Pixel, и узкий экран.
"""
import pytest
from playwright.sync_api import expect

from ui.web import PASSWORD, login

# (ширина, высота) популярных экранов + совсем узкий
DEVICES = [
    pytest.param(390, 844, id="iPhone-13"),
    pytest.param(412, 915, id="Pixel-7"),
    pytest.param(360, 740, id="narrow-360"),
]


def no_horizontal_scroll(page) -> bool:
    """Содержимое не шире окна — значит, нет горизонтальной прокрутки страницы."""
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def is_in_viewport(page, locator) -> bool:
    """Элемент целиком помещается по ширине экрана (не обрезан и не уехал за край)."""
    box = locator.bounding_box()
    width = page.viewport_size["width"]
    return box is not None and box["x"] >= 0 and box["x"] + box["width"] <= width + 1


@pytest.mark.parametrize("w, h", DEVICES)
def test_mobile_no_horizontal_scroll_and_button_visible(page, ui_user, w, h):
    """TC-058: на телефоне нет горизонтальной прокрутки, кнопка «Перевести» видна целиком"""
    page.set_viewport_size({"width": w, "height": h})
    login(page, ui_user.email, PASSWORD)
    expect(page.get_by_test_id("app-view")).to_be_visible()

    assert no_horizontal_scroll(page), "появилась горизонтальная прокрутка страницы"
    submit = page.get_by_test_id("transfer-submit")
    expect(submit).to_be_visible()
    assert is_in_viewport(page, submit), "кнопка «Перевести» выходит за край экрана"


@pytest.mark.parametrize("w, h", DEVICES)
def test_mobile_history_amount_visible(page, ui_user, recipient, w, h):
    """TC-058: суммы в истории видны полностью на узком экране"""
    page.set_viewport_size({"width": w, "height": h})
    # сделаем перевод, чтобы в истории была строка с суммой
    ui_user.client.transfer(ui_user.rub, recipient.rub, "1234.56")
    login(page, ui_user.email, PASSWORD)

    assert no_horizontal_scroll(page), "горизонтальная прокрутка страницы на экране истории"
    history = page.get_by_test_id("history")
    expect(history).to_contain_text("1 234.56")
    # таблица истории не шире экрана
    assert is_in_viewport(page, history), "таблица истории выходит за край экрана"


def test_mobile_login_with_2fa(page, make_user):
    """TC-059: вход с 2FA на мобильном экране, поле кода видно"""
    import pyotp
    user = make_user()
    secret = user.client.post("/auth/2fa/setup").json()["secret"]
    user.client.post("/auth/2fa/enable", json={"code": pyotp.TOTP(secret).now()})

    page.set_viewport_size({"width": 390, "height": 844})
    login(page, user.email, PASSWORD)
    otp_field = page.get_by_test_id("login-otp")
    expect(otp_field).to_be_visible()

    # Вводим код; если 30-секундное окно TOTP успело смениться между вводами,
    # пробуем ещё раз со свежим кодом (до 2 попыток) — иначе тест был бы «флаки».
    app_view = page.get_by_test_id("app-view")
    for _ in range(2):
        otp_field.fill(pyotp.TOTP(secret).now())
        page.get_by_test_id("login-submit").click()
        try:
            expect(app_view).to_be_visible(timeout=3000)
            break
        except AssertionError:
            pass
    expect(app_view).to_be_visible()  # проверяем только сам вход с 2FA;
    # отсутствие горизонтальной прокрутки покрыто отдельными тестами выше
