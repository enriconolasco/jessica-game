"""WebSocket sinaliza revisões; dados privados seguem no snapshot autenticado."""
import asyncio
import json

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from .rooms import RoomError


async def subscribe(connection, registry):
    room = None
    notify = None
    tasks = []
    try:
        if connection.request.path != "/updates":
            raise ValueError("Rota inválida")
        auth = json.loads(await asyncio.wait_for(connection.recv(), timeout=5))
        if not isinstance(auth, dict) or set(auth) != {"version", "code", "credential"} or type(auth["version"]) is not int or auth["version"] != 1:
            raise ValueError("Autenticação inválida")
        room = registry.get(auth["code"])
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue(maxsize=1)

        def enqueue(revision):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(revision)

        def notify(revision):
            try:
                loop.call_soon_threadsafe(enqueue, revision)
            except RuntimeError:
                pass

        with room.lock:
            room.authenticate(auth["credential"])
            if len(room.listeners) >= 16:
                raise ValueError("Limite de conexões da sala")
            room.listeners.add(notify)
            enqueue(room.revision)

        async def updates():
            while True:
                revision = await queue.get()
                await connection.send(json.dumps({"type": "room_changed", "version": 1, "revision": revision}))

        async def receive():
            await connection.recv()
            await connection.close(1008, "Ações devem usar HTTP autenticado.")

        tasks = [asyncio.create_task(updates()), asyncio.create_task(receive())]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except RoomError as exc:
        await connection.close(1008, str(exc))
    except ValueError as exc:
        reason = str(exc) if str(exc) in ("Rota inválida", "Autenticação inválida", "Limite de conexões da sala") else "Mensagem inválida."
        await connection.close(1008, reason)
    except (TypeError, KeyError, asyncio.TimeoutError):
        await connection.close(1008, "Sessão ou protocolo inválido.")
    except ConnectionClosed:
        pass
    finally:
        if room and notify:
            with room.lock:
                room.listeners.discard(notify)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def serve_notifications(registry, host, port, origins):
    return serve(lambda connection: subscribe(connection, registry), host, port,
                 origins=origins, max_size=4096, max_queue=4, compression=None,
                 open_timeout=5, close_timeout=2, ping_interval=20, ping_timeout=20)
