// Нагрузочный тест переводов PayFlow на k6.
//
// Что делает: каждый виртуальный пользователь (VU) логинится и в цикле делает переводы,
// k6 измеряет время ответа и долю ошибок.
//
// Профиль нагрузки задаётся переменной STAGE: 10, 50 или 100 пользователей.
// Запуск (из папки load):
//   docker run --rm -i --network payflow_default -e STAGE=10 -e API=http://api:8000 \
//     -v ${PWD}:/scripts grafana/k6 run /scripts/transfer_load.js
//
// thresholds — критерии приёмки (REQ-NFR-03): p95 < 500 мс, ошибок < 1%.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const API = __ENV.API || 'http://localhost:8000';
const STAGE = parseInt(__ENV.STAGE || '10', 10);

// свои метрики: доля бизнес-ошибок и время перевода
const transferErrors = new Rate('transfer_errors');
const transferDuration = new Trend('transfer_duration', true);

export const options = {
  scenarios: {
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: STAGE }, // плавный разгон
        { duration: '40s', target: STAGE }, // держим нагрузку
        { duration: '10s', target: 0 },     // спад
      ],
      gracefulRampDown: '5s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% ответов быстрее 500 мс
    transfer_errors: ['rate<0.01'],     // меньше 1% ошибок переводов
    http_req_failed: ['rate<0.01'],
  },
};

function jsonPost(path, body, token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return http.post(`${API}${path}`, JSON.stringify(body), { headers });
}

// setup() выполняется ОДИН раз до нагрузки. Здесь создаём всех пользователей и копим им баланс,
// чтобы дорогая регистрация (bcrypt) не попадала в измерение нагрузки на перевод.
// Под нагрузкой меряем именно POST /transfers — реальное бизнес-действие.
export function setup() {
  const password = 'LoadTest123!';
  function newUser(rub) {
    const email = `load-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
    jsonPost('/auth/register', { email, password });
    const token = jsonPost('/auth/login', { email, password }).json('access_token');
    const accounts = http.get(`${API}/accounts`, { headers: { Authorization: `Bearer ${token}` } }).json();
    const rubId = accounts.find((a) => a.currency === 'RUB').id;
    let left = rub;
    while (left > 0) {
      const chunk = Math.min(left, 1000000);
      jsonPost(`/accounts/${rubId}/topup`, { amount: String(chunk) }, token);
      left -= chunk;
    }
    return { token, rubId };
  }

  const recipient = newUser(0);
  // по одному отправителю на VU; каждому баланса хватит на всё время теста (переводы по 100)
  const senders = [];
  for (let i = 0; i < STAGE; i++) {
    senders.push(newUser(1000000)); // 1 млн / (100 + комиссия) ~ хватает на весь прогон
  }
  return { recipient, senders };
}

// Основная функция VU: только перевод, его и измеряем. Без регистрации в цикле.
export default function (data) {
  const sender = data.senders[(__VU - 1) % data.senders.length];
  const res = jsonPost('/transfers', {
    from_account_id: sender.rubId,
    to_account_id: data.recipient.rubId,
    amount: '100',
  }, sender.token);

  const ok = check(res, { 'transfer 201': (r) => r.status === 201 });
  transferErrors.add(!ok);
  transferDuration.add(res.timings.duration);

  sleep(1); // пауза между итерациями, имитируем реального пользователя
}
