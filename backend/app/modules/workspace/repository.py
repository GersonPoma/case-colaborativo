from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import ParametrosPaginacion, paginar
from app.modules.workspace.model import (
    Colaborador,
    EstadoColaborador,
    HistorialVersiones,
    MensajeChat,
    Proyecto,
)


class ProyectoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, proyecto_id: int) -> Proyecto | None:
        result = await self.db.execute(
            select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def list_por_dueno(
        self, id_usuario: int, params: ParametrosPaginacion
    ) -> tuple[list[Proyecto], int]:
        statement = select(Proyecto).where(
            Proyecto.id_dueno == id_usuario, Proyecto.is_deleted.is_(False)
        )
        return await paginar(self.db, statement, params)

    async def create(self, proyecto: Proyecto) -> Proyecto:
        self.db.add(proyecto)
        await self.db.flush()
        return proyecto


class ColaboradorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id_proyecto: int, id_usuario: int) -> Colaborador | None:
        result = await self.db.execute(
            select(Colaborador)
            .options(selectinload(Colaborador.usuario))
            .where(Colaborador.id_proyecto == id_proyecto, Colaborador.id_usuario == id_usuario)
        )
        return result.scalar_one_or_none()

    async def list_por_proyecto(
        self, id_proyecto: int, params: ParametrosPaginacion
    ) -> tuple[list[Colaborador], int]:
        statement = (
            select(Colaborador)
            .options(selectinload(Colaborador.usuario))
            .where(Colaborador.id_proyecto == id_proyecto)
        )
        return await paginar(self.db, statement, params)

    async def list_por_usuario(
        self, id_usuario: int, params: ParametrosPaginacion
    ) -> tuple[list[Colaborador], int]:
        statement = (
            select(Colaborador)
            .options(selectinload(Colaborador.proyecto))
            .where(
                Colaborador.id_usuario == id_usuario,
                Colaborador.estado == EstadoColaborador.ACEPTADO,
            )
        )
        return await paginar(self.db, statement, params)

    async def list_pendientes_por_usuario(
        self, id_usuario: int, params: ParametrosPaginacion
    ) -> tuple[list[Colaborador], int]:
        statement = (
            select(Colaborador)
            .options(selectinload(Colaborador.proyecto))
            .where(
                Colaborador.id_usuario == id_usuario,
                Colaborador.estado == EstadoColaborador.PENDIENTE,
            )
            .order_by(Colaborador.unido_en.desc())
        )
        return await paginar(self.db, statement, params)

    async def create(self, colaborador: Colaborador) -> Colaborador:
        self.db.add(colaborador)
        await self.db.flush()
        return colaborador

    async def delete(self, colaborador: Colaborador) -> None:
        await self.db.delete(colaborador)


class HistorialVersionesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, historial_id: int) -> HistorialVersiones | None:
        result = await self.db.execute(
            select(HistorialVersiones).where(HistorialVersiones.id == historial_id)
        )
        return result.scalar_one_or_none()

    async def list_por_proyecto(
        self, id_proyecto: int, params: ParametrosPaginacion
    ) -> tuple[list[HistorialVersiones], int]:
        statement = (
            select(HistorialVersiones)
            .where(HistorialVersiones.id_proyecto == id_proyecto)
            .order_by(HistorialVersiones.fecha.desc())
        )
        return await paginar(self.db, statement, params)

    async def create(self, historial: HistorialVersiones) -> HistorialVersiones:
        self.db.add(historial)
        await self.db.flush()
        return historial


class MensajeChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_por_proyecto(
        self, id_proyecto: int, params: ParametrosPaginacion
    ) -> tuple[list[MensajeChat], int]:
        # orden descendente a propósito: la página 1 son los mensajes más
        # recientes (para cargar el chat) y las siguientes páginas van hacia
        # atrás en el tiempo (para el scroll hacia arriba que trae mensajes viejos)
        statement = (
            select(MensajeChat)
            .options(selectinload(MensajeChat.usuario))
            .where(MensajeChat.id_proyecto == id_proyecto)
            .order_by(MensajeChat.fecha_envio.desc())
        )
        return await paginar(self.db, statement, params)

    async def create(self, mensaje: MensajeChat) -> MensajeChat:
        self.db.add(mensaje)
        await self.db.flush()
        return mensaje
