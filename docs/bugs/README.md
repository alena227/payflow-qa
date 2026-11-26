# Баг-репорты

Один файл — один дефект: `BUG-001.md`, `BUG-002.md`, … по шаблону [`_template.md`](_template.md).

| ID | Заголовок | Severity | Компонент | Тест-кейсы | Статус |
|---|---|---|---|---|---|
| [BUG-001](BUG-001.md) | Комиссия за перевод округляется вниз вместо ROUND_HALF_UP | critical | api | TC-020, TC-022, TC-023, TC-025 | New |
| [BUG-002](BUG-002.md) | Перевод на сумму, равную суточному лимиту, отклоняется | major | api | TC-029 | New |
| [BUG-003](BUG-003.md) | В событии transfer.completed amount_to — число, а не строка; все события уходят в DLQ, уведомлений нет | critical | api / Kafka | TC-045 | New |
| [BUG-004](BUG-004.md) | Событие перевода публикуется в Kafka дважды | major | api / Kafka | TC-044 | New |
| [BUG-005](BUG-005.md) | При переводе USD→RUB зачисляется сумма, округлённая вверх; баланс расходится с историей на 0.01 | critical | api / БД | TC-049 | New |
| [BUG-006](BUG-006.md) | CORS отражает любой Origin и разрешает credentials | critical | api | TC-054 | New |
| [BUG-007](BUG-007.md) | IDOR: GET /accounts/{id} возвращает чужой счёт с балансом | critical | api | TC-051 | New |
| [BUG-008](BUG-008.md) | Слабая проверка JWT: истёкшие токены, без exp, alg=none принимаются | critical | api | TC-052, TC-053 | New |
