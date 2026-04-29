"""
Modulo RabbitMQ — gestione connessione e pubblicazione messaggi.

Implementa il pattern Message Queue: il producer (FastAPI) pubblica
un messaggio sulla coda senza attendere l'elaborazione. Il consumer
(csv_worker.py) legge e processa i messaggi in modo asincrono e indipendente.
"""

import json
import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractChannel

from config import settings

CSV_IMPORT_QUEUE = "csv_import"

_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None


async def connect() -> None:
    """
    Apre la connessione a RabbitMQ e il canale di comunicazione.
    """
    global _connection, _channel
    _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    _channel = await _connection.channel()
    await _channel.set_qos(prefetch_count=10)
    await _channel.declare_queue(CSV_IMPORT_QUEUE, durable=True)


async def close() -> None:
    """
    Chiude la connessione a RabbitMQ.

    Chiamata nel lifespan di FastAPI allo shutdown del server.
    """
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()


async def publish(queue_name: str, message: dict) -> None:
    """
    Pubblica un messaggio JSON su una coda RabbitMQ.

    Usa il default exchange con routing_key = nome della coda (direct routing).
    Il messaggio è marcato PERSISTENT --> viene salvato su disco dal broker e
    non viene perso in caso di chiusura RabbitMQ.
    """
    if _channel is None:
        raise RuntimeError("Canale RabbitMQ non inizializzato. Chiamare connect() prima.")

    await _channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=queue_name,
    )
