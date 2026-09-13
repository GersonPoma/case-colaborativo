from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.model import Perfil, Usuario


class UsuarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Usuario | None:
        result = await self.db.execute(
            select(Usuario).options(selectinload(Usuario.perfil)).where(Usuario.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Usuario | None:
        result = await self.db.execute(
            select(Usuario)
            .options(selectinload(Usuario.perfil))
            .where(Usuario.username == username)
        )
        return result.scalar_one_or_none()

    async def create(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        await self.db.flush()
        return usuario


class PerfilRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Perfil | None:
        result = await self.db.execute(select(Perfil).where(Perfil.email == email))
        return result.scalar_one_or_none()

    async def create(self, perfil: Perfil) -> Perfil:
        self.db.add(perfil)
        await self.db.flush()
        return perfil
