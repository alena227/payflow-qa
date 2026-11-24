"""Публикация событий в Kafka (Redpanda).

После успешного перевода api отправляет в топик `transactions` событие transfer.completed.
- key = tx_id: все события одной операции попадают в одну партицию (сохраняется порядок);
- value = JSON по схеме app/notifier/transaction_event.schema.json;
- заголовок request_id — чтобы связать событие с HTTP-запросом в логах.
Суммы передаются строками ("100.00"), чтобы не терять точность.

Ограничение учебного стенда: событие отправляется после COMMIT в базе. Если Kafka недоступна,
перевод останется в базе, а событие потеряется (в проде для этого используют паттерн outbox).
"""
import datetime as dt
import json
import logging
import os
import uuid

from confluent_kafka import KafkaException, Producer

from .flags import BUGS
from .logging_setup import request_id_var

TOPIC = "transactions"
log = logging.getLogger("api.events")
_producer: Producer | None = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092"),
            "acks": "all",
            "enable.idempotence": True,
            "message.timeout.ms": 5000,
        })
    return _producer


def _on_delivery(err, msg) -> None:
    if err is not None:
        log.error("event delivery failed", extra={"extra_fields": {"error": str(err)}})
    else:
        log.info("event delivered", extra={"extra_fields": {
            "topic": msg.topic(), "partition": msg.partition(), "offset": msg.offset(),
        }})


def build_transfer_event(tx: dict, from_user_id: int, to_user_id: int) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "transfer.completed",
        "occurred_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tx_id": str(tx["id"]),
        "from_account_id": tx["from_account_id"],
        "to_account_id": tx["to_account_id"],
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "amount": str(tx["amount"]),
        "currency": tx["currency"],
        "fee": str(tx["fee"]),
        "amount_to": float(tx["amount_to"]) if BUGS else str(tx["amount_to"]),
        "currency_to": tx["currency_to"],
        "rate": str(tx["rate"]) if tx["rate"] is not None else None,
    }


def publish_transfer_event(tx: dict, from_user_id: int, to_user_id: int) -> None:
    event = build_transfer_event(tx, from_user_id, to_user_id)
    payload = json.dumps(event).encode()
    headers = [("request_id", request_id_var.get().encode()), ("event_type", b"transfer.completed")]
    attempts = 2 if BUGS and event["currency"] != event["currency_to"] else 1
    try:
        producer = get_producer()
        for _ in range(attempts):
            producer.produce(TOPIC, key=event["tx_id"].encode(), value=payload, headers=headers,
                             on_delivery=_on_delivery)
        not_sent = producer.flush(5)
        if not_sent:
            log.error("event not delivered in time", extra={"extra_fields": {"tx_id": event["tx_id"]}})
    except (KafkaException, BufferError) as e:
        log.error("kafka publish error", extra={"extra_fields": {"tx_id": event["tx_id"], "error": str(e)}})
