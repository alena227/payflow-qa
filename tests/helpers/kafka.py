"""Работа с Kafka (Redpanda) в тестах через библиотеку confluent-kafka (та же, что в приложении).

Главная идея — «встать в конец топика ДО действия»:
    watcher = TopicWatcher("transactions")   # запомнили текущий конец каждой партиции
    ...делаем перевод через API...
    events = watcher.collect(lambda m: m.key == tx_id)   # читаем только то, что появилось после
Так тест видит только свои сообщения, а не всю историю топика.

Почему не kafka-python: на Windows + Python 3.14 он молча не находил партиции при ручном
назначении (assign) и тест зависал. confluent-kafka работает через librdkafka и такой проблемы нет.
"""
import json
import os
import time
import uuid

from confluent_kafka import Consumer, Producer, TopicPartition

BOOTSTRAP = os.getenv("PAYFLOW_KAFKA", "127.0.0.1:19092")


class Message:
    """Упрощенное сообщение: key как строка, headers как dict."""

    def __init__(self, msg):
        self.topic = msg.topic()
        self.partition = msg.partition()
        self.offset = msg.offset()
        self.key = msg.key().decode() if msg.key() else None
        self.raw_value = msg.value()
        self.headers = {k: (v.decode() if v else "") for k, v in (msg.headers() or [])}

    @property
    def value(self) -> str | None:
        return self.raw_value.decode(errors="replace") if self.raw_value is not None else None

    def json(self) -> dict:
        return json.loads(self.raw_value)


class TopicWatcher:
    def __init__(self, topic: str):
        # Уникальная group.id и без коммитов: читаем «сами по себе», не мешая notifier
        self.consumer = Consumer({
            "bootstrap.servers": BOOTSTRAP,
            "group.id": f"qa-watcher-{uuid.uuid4().hex[:8]}",
            "enable.auto.commit": False,
        })
        partitions = self.consumer.list_topics(topic, timeout=10).topics[topic].partitions
        start = []
        for p in partitions:
            # high watermark = offset, под которым будет записано СЛЕДУЮЩЕЕ сообщение партиции
            _, high = self.consumer.get_watermark_offsets(TopicPartition(topic, p), timeout=10)
            start.append(TopicPartition(topic, p, high))
        self.consumer.assign(start)

    def collect(self, match, timeout: float = 10.0, settle: float = 2.0) -> list[Message]:
        """Читает новые сообщения, оставляет подходящие под match.

        После первого найденного ждем еще `settle` секунд — чтобы поймать возможные дубли.
        """
        found: list[Message] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = self.consumer.poll(0.3)
            if msg is not None and not msg.error():
                m = Message(msg)
                if match(m):
                    found.append(m)
            if found and deadline - time.monotonic() > settle:
                deadline = time.monotonic() + settle
        self.consumer.close()
        return found


def produce(topic: str, value: bytes, key: bytes | None = None) -> None:
    producer = Producer({"bootstrap.servers": BOOTSTRAP})
    producer.produce(topic, value=value, key=key)
    assert producer.flush(10) == 0, "сообщение не отправлено в Kafka"


def unique_marker() -> str:
    return f"qa-{uuid.uuid4().hex[:12]}"
