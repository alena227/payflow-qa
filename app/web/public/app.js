// PayFlow web: простой клиент к API. Токен хранится в sessionStorage (живет до закрытия вкладки).
const API = window.PAYFLOW_API || "http://localhost:8000";
const $ = (sel) => document.querySelector(sel);

let token = null;
try { token = sessionStorage.getItem("token"); } catch (e) { /* storage недоступен */ }

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = "Bearer " + token;
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const d = data && data.detail;
    const msg = Array.isArray(d) ? d.map((x) => x.msg).join("; ") : (d || "Ошибка " + res.status);
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

// "12345.60" -> "12 345.60" (без float: работаем со строкой)
function money(value, currency) {
  const [int, frac = "00"] = String(value).split(".");
  const sign = int.startsWith("-") ? "−" : "";
  const digits = int.replace("-", "").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${sign}${digits}.${frac.padEnd(2, "0")} ${currency === "RUB" ? "₽" : "$"}`;
}

function setToken(t) {
  token = t;
  try { t ? sessionStorage.setItem("token", t) : sessionStorage.removeItem("token"); } catch (e) {}
}

function show(view) {
  $("#login-view").hidden = view !== "login";
  $("#app-view").hidden = view !== "app";
  $("#logout").hidden = view !== "app";
}

// ---------- вход ----------
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const body = { email: f.email.value.trim(), password: f.password.value };
  if (!$("#otp-row").hidden) body.otp = f.otp.value.trim();
  $("#login-error").textContent = "";
  try {
    const r = await api("POST", "/auth/login", body);
    setToken(r.access_token);
    f.reset();
    $("#otp-row").hidden = true;
    await loadApp();
  } catch (err) {
    if (err.message === "otp required") {
      $("#otp-row").hidden = false;
      f.otp.focus();
      $("#login-error").textContent = "Введите 6-значный код из приложения";
    } else if (err.status === 429) {
      $("#login-error").textContent = "Слишком много попыток. Попробуйте позже";
    } else if (err.message === "invalid otp") {
      $("#login-error").textContent = "Неверный код";
    } else if (err.status === 401) {
      $("#login-error").textContent = "Неверный email или пароль";
    } else {
      $("#login-error").textContent = err.message;
    }
  }
});

$("#logout").addEventListener("click", () => {
  setToken(null);
  $("#user-email").textContent = "";
  show("login");
});

// ---------- основное ----------
async function loadApp() {
  try {
    const me = await api("GET", "/auth/me");
    $("#user-email").textContent = me.email;
    show("app");
    await Promise.all([loadAccounts(), loadHistory(), loadNotifications()]);
  } catch (err) {
    setToken(null);
    show("login");
  }
}

async function loadAccounts() {
  const accounts = await api("GET", "/accounts");
  $("#accounts").innerHTML = accounts.map((a) => `
    <div class="account" data-testid="account-${a.currency}">
      <div class="acc-cur">${a.currency} · счет №${a.id}</div>
      <div class="acc-balance" data-testid="balance-${a.currency}">${money(a.balance, a.currency)}</div>
    </div>`).join("");
  $("#transfer-form").from.innerHTML = accounts
    .map((a) => `<option value="${a.id}">№${a.id} · ${a.currency} · ${money(a.balance, a.currency)}</option>`)
    .join("");
}

function describe(t) {
  if (t.type === "topup") return "Пополнение";
  if (t.direction === "out") return `Перевод на счет №${t.to_account_id}`;
  if (t.direction === "in") return `Перевод со счета №${t.from_account_id}`;
  return `Между своими счетами №${t.from_account_id} → №${t.to_account_id}`;
}

async function loadHistory() {
  const items = await api("GET", "/transactions?limit=20");
  $("#history-body").innerHTML = items.length ? items.map((t) => {
    const out = t.direction === "out";
    const sum = out ? "−" + money(t.amount, t.currency) : "+" + money(t.amount_to, t.currency_to);
    const fee = t.type === "transfer" && t.direction !== "in" ? money(t.fee, t.currency) : "—";
    return `<tr data-testid="history-row">
      <td>${new Date(t.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}</td>
      <td>${describe(t)}</td>
      <td class="amount ${out ? "neg" : "pos"}">${sum}</td>
      <td class="amount">${fee}</td>
    </tr>`;
  }).join("") : `<tr><td colspan="4" class="empty">Операций пока нет</td></tr>`;
}

async function loadNotifications() {
  const items = await api("GET", "/notifications?limit=10");
  $("#notifications").innerHTML = items.length
    ? items.map((n) => `<li data-testid="notification">${escapeHtml(n.message)}</li>`).join("")
    : `<li class="empty">Нет уведомлений</li>`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

$("#transfer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const result = $("#transfer-result");
  result.className = "msg";
  result.textContent = "";
  const amount = f.amount.value.trim().replace(",", ".");
  try {
    const t = await api("POST", "/transfers", {
      from_account_id: Number(f.from.value),
      to_account_id: Number(f.to.value),
      amount,
    });
    result.classList.add("ok");
    result.textContent = `Готово: ${money(t.amount, t.currency)}, комиссия ${money(t.fee, t.currency)}` +
      (t.currency !== t.currency_to ? `, зачислено ${money(t.amount_to, t.currency_to)}` : "");
    f.amount.value = "";
    await Promise.all([loadAccounts(), loadHistory()]);
    setTimeout(loadNotifications, 1500); // уведомление создается асинхронно через Kafka
  } catch (err) {
    result.classList.add("err");
    result.textContent = err.message;
  }
});

token ? loadApp() : show("login");
