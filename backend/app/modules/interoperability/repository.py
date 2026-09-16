from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interoperability.model import ConfiguracionTranspilacion


class ConfiguracionTranspilacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_proyecto(self, id_proyecto: int) -> ConfiguracionTranspilacion | None:
        result = await self.db.execute(
            select(ConfiguracionTranspilacion).where(
                ConfiguracionTranspilacion.id_proyecto == id_proyecto,
                ConfiguracionTranspilacion.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
