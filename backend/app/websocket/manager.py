from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._conexiones: dict[int, list[WebSocket]] = {}

    async def conectar(self, proyecto_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._conexiones.setdefault(proyecto_id, []).append(websocket)

    def desconectar(self, proyecto_id: int, websocket: WebSocket) -> None:
        conexiones = self._conexiones.get(proyecto_id)
        if not conexiones:
            return
        if websocket in conexiones:
            conexiones.remove(websocket)
        if not conexiones:
            del self._conexiones[proyecto_id]

    async def difundir(self, proyecto_id: int, mensaje: dict, excluir: WebSocket | None = None) -> None:
        for conexion in list(self._conexiones.get(proyecto_id, [])):
            if conexion is excluir:
                continue
            try:
                await conexion.send_json(mensaje)
            except Exception:
                self.desconectar(proyecto_id, conexion)

    def conectados(self, proyecto_id: int) -> int:
        return len(self._conexiones.get(proyecto_id, []))


manager = ConnectionManager()
