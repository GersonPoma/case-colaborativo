from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import ParametrosPaginacion
from app.modules.auth.repository import UsuarioRepository
from app.modules.workspace.model import (
    Colaborador,
    EstadoColaborador,
    HistorialVersiones,
    MensajeChat,
    Proyecto,
    RolColaborador,
)
from app.modules.workspace.repository import (
    ColaboradorRepository,
    HistorialVersionesRepository,
    MensajeChatRepository,
    ProyectoRepository,
)
from app.modules.workspace.schema import (
    CambiarRolColaborador,
    CrearProyecto,
    EnviarMensaje,
    InvitarColaborador,
    MensajeChatRespuesta,
    ResponderInvitacion,
)
from app.websocket.manager import manager


class ProyectoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.proyecto_repository = ProyectoRepository(db)
        self.colaborador_repository = ColaboradorRepository(db)

    async def crear(self, datos: CrearProyecto, id_dueno: int) -> Proyecto:
        proyecto = Proyecto(nombre=datos.nombre, descripcion=datos.descripcion, id_dueno=id_dueno)
        await self.proyecto_repository.create(proyecto)
        await self.db.commit()
        await self.db.refresh(proyecto)
        return proyecto

    async def listar_propios(
        self, id_usuario: int, params: ParametrosPaginacion
    ) -> tuple[list[Proyecto], int]:
        return await self.proyecto_repository.list_por_dueno(id_usuario, params)

    async def obtener(self, proyecto_id: int) -> Proyecto:
        proyecto = await self.proyecto_repository.get_by_id(proyecto_id)
        if proyecto is None:
            raise NotFoundError("Proyecto no encontrado")
        return proyecto

    async def verificar_dueno(self, proyecto: Proyecto, id_usuario: int) -> None:
        if proyecto.id_dueno != id_usuario:
            raise ForbiddenError("Solo el dueño del proyecto puede realizar esta acción")

    async def verificar_miembro(self, proyecto: Proyecto, id_usuario: int) -> None:
        if proyecto.id_dueno == id_usuario:
            return
        colaborador = await self.colaborador_repository.get(proyecto.id, id_usuario)
        if colaborador is None or colaborador.estado != EstadoColaborador.ACEPTADO:
            raise ForbiddenError("No tienes acceso a este proyecto")

    async def verificar_editor(self, proyecto: Proyecto, id_usuario: int) -> None:
        if proyecto.id_dueno == id_usuario:
            return
        colaborador = await self.colaborador_repository.get(proyecto.id, id_usuario)
        if (
            colaborador is None
            or colaborador.estado != EstadoColaborador.ACEPTADO
            or colaborador.rol != RolColaborador.EDITOR
        ):
            raise ForbiddenError("No tienes permisos de edición en este proyecto")

    async def eliminar(self, proyecto_id: int, id_usuario: int) -> None:
        proyecto = await self.obtener(proyecto_id)
        await self.verificar_dueno(proyecto, id_usuario)
        proyecto.is_deleted = True
        await self.db.commit()


class ColaboradorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.colaborador_repository = ColaboradorRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.proyecto_service = ProyectoService(db)

    async def listar_colaboraciones(
        self, id_usuario: int, params: ParametrosPaginacion
    ) -> tuple[list[Colaborador], int]:
        return await self.colaborador_repository.list_por_usuario(id_usuario, params)

    async def listar_colaboradores(
        self, proyecto_id: int, id_usuario_solicitante: int, params: ParametrosPaginacion
    ) -> tuple[list[Colaborador], int]:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_miembro(proyecto, id_usuario_solicitante)
        return await self.colaborador_repository.list_por_proyecto(proyecto_id, params)

    async def invitar(
        self, proyecto_id: int, id_dueno_solicitante: int, datos: InvitarColaborador
    ) -> Colaborador:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_dueno(proyecto, id_dueno_solicitante)

        usuario = await self.usuario_repository.get_by_username(datos.username)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado")

        if usuario.id == proyecto.id_dueno:
            raise ConflictError("El dueño ya tiene acceso total al proyecto")

        existente = await self.colaborador_repository.get(proyecto_id, usuario.id)
        if existente is not None:
            if existente.estado == EstadoColaborador.ACEPTADO:
                raise ConflictError("El usuario ya es colaborador de este proyecto")
            if existente.estado == EstadoColaborador.PENDIENTE:
                raise ConflictError("El usuario ya tiene una invitación pendiente")

            # RECHAZADO: se reenvía la invitación reutilizando la misma fila
            existente.estado = EstadoColaborador.PENDIENTE
            existente.rol = datos.rol
            await self.db.commit()
            await self.db.refresh(existente)
            existente.usuario = usuario
            return existente

        colaborador = Colaborador(
            id_proyecto=proyecto_id,
            id_usuario=usuario.id,
            rol=datos.rol,
            estado=EstadoColaborador.PENDIENTE,
        )
        await self.colaborador_repository.create(colaborador)
        await self.db.commit()
        await self.db.refresh(colaborador)
        colaborador.usuario = usuario
        return colaborador

    async def listar_invitaciones_pendientes(
        self, id_usuario: int, params: ParametrosPaginacion
    ) -> tuple[list[Colaborador], int]:
        return await self.colaborador_repository.list_pendientes_por_usuario(id_usuario, params)

    async def responder_invitacion(
        self, proyecto_id: int, id_usuario_invitado: int, datos: ResponderInvitacion
    ) -> Colaborador:
        colaborador = await self.colaborador_repository.get(proyecto_id, id_usuario_invitado)
        if colaborador is None or colaborador.estado != EstadoColaborador.PENDIENTE:
            raise NotFoundError("No tienes una invitación pendiente para este proyecto")

        if datos.aceptar:
            colaborador.estado = EstadoColaborador.ACEPTADO
            colaborador.unido_en = datetime.now(timezone.utc)
        else:
            colaborador.estado = EstadoColaborador.RECHAZADO

        await self.db.commit()
        await self.db.refresh(colaborador)
        return colaborador

    async def cambiar_rol(
        self,
        proyecto_id: int,
        id_dueno_solicitante: int,
        id_usuario_colaborador: int,
        datos: CambiarRolColaborador,
    ) -> Colaborador:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_dueno(proyecto, id_dueno_solicitante)

        colaborador = await self.colaborador_repository.get(proyecto_id, id_usuario_colaborador)
        if colaborador is None:
            raise NotFoundError("El usuario no es colaborador de este proyecto")

        colaborador.rol = datos.rol
        await self.db.commit()
        return colaborador

    async def quitar(
        self, proyecto_id: int, id_dueno_solicitante: int, id_usuario_colaborador: int
    ) -> None:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_dueno(proyecto, id_dueno_solicitante)

        colaborador = await self.colaborador_repository.get(proyecto_id, id_usuario_colaborador)
        if colaborador is None:
            raise NotFoundError("El usuario no es colaborador de este proyecto")

        await self.colaborador_repository.delete(colaborador)
        await self.db.commit()


class HistorialVersionesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.historial_repository = HistorialVersionesRepository(db)
        self.proyecto_service = ProyectoService(db)

    async def listar(
        self, proyecto_id: int, id_dueno_solicitante: int, params: ParametrosPaginacion
    ) -> tuple[list[HistorialVersiones], int]:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_dueno(proyecto, id_dueno_solicitante)
        return await self.historial_repository.list_por_proyecto(proyecto_id, params)

    async def crear_snapshot(
        self, proyecto_id: int, snapshot_lienzo: dict, id_usuario_creador: int
    ) -> HistorialVersiones:
        historial = HistorialVersiones(
            id_proyecto=proyecto_id,
            snapshot_lienzo=snapshot_lienzo,
            creado_por=id_usuario_creador,
        )
        await self.historial_repository.create(historial)
        await self.db.commit()
        return historial

    async def crear_version(
        self, proyecto_id: int, id_usuario_creador: int
    ) -> HistorialVersiones:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_editor(proyecto, id_usuario_creador)

        snapshot = proyecto.estado_lienzo or {
            "diagrama_id": str(proyecto.id),
            "clases": {},
            "relaciones": {},
        }
        return await self.crear_snapshot(proyecto_id, snapshot, id_usuario_creador)

    async def obtener_lienzo(
        self, proyecto_id: int, id_dueno_solicitante: int, historial_id: int
    ) -> dict:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_dueno(proyecto, id_dueno_solicitante)

        historial = await self.historial_repository.get_by_id(historial_id)
        if historial is None or historial.id_proyecto != proyecto_id:
            raise NotFoundError("Versión no encontrada")

        return historial.snapshot_lienzo

    async def restaurar(
        self, proyecto_id: int, id_dueno_solicitante: int, historial_id: int
    ) -> Proyecto:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_dueno(proyecto, id_dueno_solicitante)

        historial = await self.historial_repository.get_by_id(historial_id)
        if historial is None or historial.id_proyecto != proyecto_id:
            raise NotFoundError("Versión no encontrada")

        proyecto.estado_lienzo = historial.snapshot_lienzo
        await self.db.commit()
        await self.db.refresh(proyecto)
        return proyecto


class MensajeChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mensaje_repository = MensajeChatRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.proyecto_service = ProyectoService(db)

    async def listar(
        self, proyecto_id: int, id_usuario_solicitante: int, params: ParametrosPaginacion
    ) -> tuple[list[MensajeChat], int]:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_miembro(proyecto, id_usuario_solicitante)
        return await self.mensaje_repository.list_por_proyecto(proyecto_id, params)

    async def enviar(self, proyecto_id: int, id_usuario: int, datos: EnviarMensaje) -> MensajeChat:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_miembro(proyecto, id_usuario)

        mensaje = MensajeChat(
            id_proyecto=proyecto_id, id_usuario=id_usuario, contenido=datos.contenido
        )
        await self.mensaje_repository.create(mensaje)
        await self.db.commit()
        await self.db.refresh(mensaje)
        mensaje.usuario = await self.usuario_repository.get_by_id(id_usuario)

        payload = MensajeChatRespuesta.model_validate(mensaje).model_dump(mode="json")
        await manager.difundir(proyecto_id, {"tipo": "MENSAJE_CHAT", "mensaje": payload})

        return mensaje
