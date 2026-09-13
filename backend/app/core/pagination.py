from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class ParametrosPaginacion:
    def __init__(self, pagina: int = Query(1, ge=1), tamano: int = Query(20, ge=1, le=100)):
        self.pagina = pagina
        self.tamano = tamano

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamano


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    pagina: int
    tamano: int
    total_paginas: int


async def paginar(
    db: AsyncSession, statement: Select, params: ParametrosPaginacion
) -> tuple[list, int]:
    total = await db.scalar(select(func.count()).select_from(statement.subquery()))
    total = total or 0

    resultado = await db.execute(statement.offset(params.offset).limit(params.tamano))
    items = list(resultado.scalars().all())

    return items, total


def construir_pagina(items: list, total: int, params: ParametrosPaginacion) -> Pagina:
    total_paginas = (total + params.tamano - 1) // params.tamano if params.tamano else 0
    return Pagina(
        items=items, total=total, pagina=params.pagina, tamano=params.tamano,
        total_paginas=total_paginas,
    )
