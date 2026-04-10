from queue import Empty, Queue
from threading import Event
from typing import Any, Callable, Dict, Optional


StateCommand = Dict[str, Any]

_queue: "Queue[StateCommand]" = Queue()
_dispatcher: Optional[Callable[[str, Dict[str, Any]], Any]] = None


def register_dispatcher(dispatcher: Callable[[str, Dict[str, Any]], Any]) -> None:
    global _dispatcher
    _dispatcher = dispatcher


def submit(command_type: str, payload: Optional[Dict[str, Any]] = None, wait: bool = False, timeout: float = 30.0):
    command: StateCommand = {
        "type": command_type,
        "payload": payload or {},
    }

    if wait:
        command["event"] = Event()

    _queue.put(command)

    if not wait:
        return {"status": "queued", "type": command_type}

    event = command["event"]
    if not event.wait(timeout):
        return {"status": "error", "message": f"State command timed out: {command_type}"}
    return command.get("result")


def process_all(limit: Optional[int] = None) -> int:
    if _dispatcher is None:
        return 0

    processed = 0
    while limit is None or processed < limit:
        try:
            command = _queue.get_nowait()
        except Empty:
            break

        try:
            result = _dispatcher(command["type"], command.get("payload", {}))
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}

        command["result"] = result
        event = command.get("event")
        if event:
            event.set()

        processed += 1

    return processed
