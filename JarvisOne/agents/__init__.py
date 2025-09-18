import asyncio
from typing import Set, Any, List

try:
	from fastapi import WebSocket
	from starlette.websockets import WebSocketState
except Exception:  # typing only
	WebSocket = object  # type: ignore
	WebSocketState = None  # type: ignore


class BoardAgentManager:
	"""
	Minimal in-process WS client manager so the backend can broadcast
	lightweight events like {"type":"new_message"} to connected UIs.
	"""
	def __init__(self) -> None:
		self._clients = set()
		self._lock = asyncio.Lock()
		self._bg_task = None

	def user_joined(self, websocket: Any) -> None:
		self._clients.add(websocket)

	def user_left(self, websocket: Any) -> None:
		if websocket in self._clients:
			self._clients.remove(websocket)

	async def notify_clients(self) -> None:
		# Broadcast a simple tick that causes UIs to refetch
		payload = '{"type":"new_message"}'
		stale: List[Any] = []
		for ws in list(self._clients):
			try:
				# Check if still connected
				if hasattr(ws, "client_state") and WebSocketState and ws.client_state != WebSocketState.CONNECTED:
					stale.append(ws)
					continue
				await ws.send_text(payload)
			except Exception:
				stale.append(ws)
		for ws in stale:
			self.user_left(ws)

	async def start_cycle(self):
		# Placeholder for a background loop if needed later
		await self.notify_clients()


board_agent = BoardAgentManager()


def start_background_board_loop() -> None:
	# No-op for now; reserved for future periodic cycles
	return None


def stop_background_board_loop() -> None:
	# No-op placeholder
	return None
