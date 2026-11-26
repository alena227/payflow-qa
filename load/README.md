# Нагрузочное тестирование (k6)

Проверяем `POST /transfers` под нагрузкой 10 / 50 / 100 виртуальных пользователей.
Критерии (REQ-NFR-03): p95 времени ответа < 500 мс, доля ошибок < 1%.

## Запуск через Docker (k6 ставить не нужно)
Стенд должен быть поднят (`docker compose up -d`). Из папки `load`:

```powershell
docker run --rm -i --network payflow_default -e STAGE=10 -e API=http://api:8000 -v ${PWD}:/scripts grafana/k6 run /scripts/transfer_load.js
```
Поменяй `STAGE` на 50 и 100 для других уровней нагрузки.
`--network payflow_default` подключает k6 к сети проекта, поэтому адрес api — `http://api:8000`.

## Что меряем
- `http_req_duration` p95 — 95-й перцентиль времени ответа (95% запросов быстрее этого);
- `http_req_failed` — доля HTTP-ошибок;
- `transfer_errors` — доля переводов, не завершившихся 201;
- `transfer_duration` — время самого перевода.

## Результаты
Смотри [docs/load-report.md](../docs/load-report.md).

## Тяжёлые прогоны
100 VU и полный прогон лучше запускать в GitHub Actions (день 12), а не на ноутбуке.
