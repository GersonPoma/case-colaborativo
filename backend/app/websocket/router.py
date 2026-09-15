from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.modules.auth.repository import UsuarioRepository
from app.modules.canvas.schema import (
    AccionCanvas,
    AgregarAtributo,
    AgregarMetodo,
    AlinearNodos,
    CrearClase,
    EditarAtributo,
    EditarClase,
    EditarMetodo,
    EditarRelacion,
    EliminarAtributo,
    EliminarClase,
    EliminarMetodo,
    EliminarRelacion,
    MensajeEntrante,
    MensajeError,
    MensajeSaliente,
    ModificarUI,
    TrazarRelacion,
)
from app.modules.canvas.service import CanvasService
from app.modules.workspace.service import ProyectoService
from app.websocket.manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])

_ESQUEMA_POR_ACCION = {
    AccionCanvas.CREAR_CLASE: CrearClase,
    AccionCanvas.EDITAR_CLASE: EditarClase,
    AccionCanvas.ELIMINAR_CLASE: EliminarClase,
    AccionCanvas.AGREGAR_ATRIBUTO: AgregarAtributo,
    AccionCanvas.EDITAR_ATRIBUTO: EditarAtributo,
    AccionCanvas.ELIMINAR_ATRIBUTO: EliminarAtributo,
    AccionCanvas.AGREGAR_METODO: AgregarMetodo,
    AccionCanvas.EDITAR_METODO: EditarMetodo,
    AccionCanvas.ELIMINAR_METODO: EliminarMetodo,
    AccionCanvas.TRAZAR_RELACION: TrazarRelacion,
    AccionCanvas.EDITAR_RELACION: EditarRelacion,
    AccionCanvas.ELIMINAR_RELACION: EliminarRelacion,
    AccionCanvas.MODIFICAR_UI: ModificarUI,
    AccionCanvas.ALINEAR_NODOS: AlinearNodos,
}


async def _ejecutar_accion(
    canvas_service: CanvasService, proyecto_id: int, accion: AccionCanvas, datos: dict
) -> dict:
    esquema = _ESQUEMA_POR_ACCION[accion]
    payload = esquema.model_validate(datos)
    metodo = getattr(canvas_service, accion.value.lower())
    return await metodo(proyecto_id, payload)


@router.websocket("/proyectos/{proyecto_id}")
async def canvas_websocket(
    websocket: WebSocket,
    proyecto_id: int,
    db: AsyncSession = Depends(get_db),
):
    token = websocket.query_params.get("token")
    usuario = None
    if token:
        user_id = decode_access_token(token)
        if user_id is not None:
            usuario = await UsuarioRepository(db).get_by_id(int(user_id))

    if usuario is None:
        await websocket.close(code=4401)
        return

    usuario_id = usuario.id

    proyecto_service = ProyectoService(db)
    try:
        proyecto = await proyecto_service.obtener(proyecto_id)
        await proyecto_service.verificar_miembro(proyecto, usuario_id)
    except AppException:
        await websocket.close(code=4403)
        return

    puede_editar = True
    try:
        await proyecto_service.verificar_editor(proyecto, usuario_id)
    except AppException:
        puede_editar = False

    # cierra la transacción de los checks de arriba para no dejarla abierta mientras espera mensajes
    await db.rollback()

    canvas_service = CanvasService(db)

    await manager.conectar(proyecto_id, websocket)
    try:
        while True:
            bruto = await websocket.receive_json()

            try:
                mensaje = MensajeEntrante.model_validate(bruto)
            except ValidationError as e:
                await websocket.send_json(MensajeError(error=str(e)).model_dump())
                continue

            if not puede_editar:
                await websocket.send_json(
                    MensajeError(error="No tienes permisos de edición en este proyecto").model_dump()
                )
                continue

            try:
                resultado = await _ejecutar_accion(
                    canvas_service, proyecto_id, mensaje.accion, mensaje.datos
                )
            except ValidationError as e:
                await websocket.send_json(MensajeError(error=str(e)).model_dump())
                continue
            except AppException as e:
                await websocket.send_json(MensajeError(error=e.message).model_dump())
                continue

            salida = MensajeSaliente(accion=mensaje.accion, datos=resultado, usuario_id=usuario_id)
            await manager.difundir(proyecto_id, salida.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        manager.desconectar(proyecto_id, websocket)
