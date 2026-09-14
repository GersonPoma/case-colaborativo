import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.canvas.schema import (
    AgregarAtributo,
    AlinearNodos,
    CrearClase,
    EditarAtributo,
    EditarClase,
    EliminarAtributo,
    EliminarClase,
    EliminarRelacion,
    ModificarUI,
    TrazarRelacion,
)
from app.modules.workspace.model import Proyecto
from app.modules.workspace.repository import ProyectoRepository


class CanvasService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.proyecto_repository = ProyectoRepository(db)

    async def _obtener_estado(self, proyecto_id: int) -> tuple[Proyecto, dict]:
        proyecto = await self.proyecto_repository.get_by_id(proyecto_id)
        if proyecto is None:
            raise NotFoundError("Proyecto no encontrado")

        actual = proyecto.estado_lienzo
        if actual:
            # copia superficial: para que SQLAlchemy detecte el cambio hace falta
            # reasignar un objeto nuevo, mutar el dict existente in-place no se persiste
            estado = dict(actual)
        else:
            estado = {"diagrama_id": str(proyecto.id), "clases": {}, "relaciones": {}}

        return proyecto, estado

    async def _guardar_estado(self, proyecto: Proyecto, estado: dict) -> None:
        proyecto.estado_lienzo = estado
        await self.db.commit()

    async def crear_clase(self, proyecto_id: int, datos: CrearClase) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase_id = str(uuid.uuid4())
        clase = {
            "id": clase_id,
            "nombre": datos.nombre,
            "atributos": {},
            "ui": {"x": datos.x, "y": datos.y, "ancho": 220, "color": "#e3f2fd"},
        }
        estado["clases"] = {**estado["clases"], clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return clase

    async def editar_clase(self, proyecto_id: int, datos: EditarClase) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None:
            raise NotFoundError("Clase no encontrada")

        clase = {**clase, "nombre": datos.nombre}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return clase

    async def eliminar_clase(self, proyecto_id: int, datos: EliminarClase) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        if datos.clase_id not in estado["clases"]:
            raise NotFoundError("Clase no encontrada")

        clases = dict(estado["clases"])
        del clases[datos.clase_id]
        estado["clases"] = clases

        estado["relaciones"] = {
            rid: r
            for rid, r in estado["relaciones"].items()
            if r["origen_id"] != datos.clase_id and r["destino_id"] != datos.clase_id
        }

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id}

    async def agregar_atributo(self, proyecto_id: int, datos: AgregarAtributo) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None:
            raise NotFoundError("Clase no encontrada")

        atributo_id = str(uuid.uuid4())
        atributo = {
            "id": atributo_id,
            "nombre": datos.nombre,
            "tipo": datos.tipo,
            "es_pk": datos.es_pk,
            "orden": len(clase["atributos"]),
        }
        clase = {**clase, "atributos": {**clase["atributos"], atributo_id: atributo}}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "atributo": atributo}

    async def editar_atributo(self, proyecto_id: int, datos: EditarAtributo) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None or datos.atributo_id not in clase["atributos"]:
            raise NotFoundError("Atributo no encontrado")

        atributo_anterior = clase["atributos"][datos.atributo_id]
        atributo = {
            **atributo_anterior,
            "nombre": datos.nombre,
            "tipo": datos.tipo,
            "es_pk": datos.es_pk,
        }
        clase = {**clase, "atributos": {**clase["atributos"], datos.atributo_id: atributo}}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "atributo": atributo}

    async def eliminar_atributo(self, proyecto_id: int, datos: EliminarAtributo) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None or datos.atributo_id not in clase["atributos"]:
            raise NotFoundError("Atributo no encontrado")

        atributos = dict(clase["atributos"])
        del atributos[datos.atributo_id]
        clase = {**clase, "atributos": atributos}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "atributo_id": datos.atributo_id}

    async def trazar_relacion(self, proyecto_id: int, datos: TrazarRelacion) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        if datos.origen_id not in estado["clases"] or datos.destino_id not in estado["clases"]:
            raise NotFoundError("La clase de origen o destino no existe")

        relacion_id = str(uuid.uuid4())
        relacion = {
            "id": relacion_id,
            "origen_id": datos.origen_id,
            "destino_id": datos.destino_id,
            "tipo": datos.tipo,
            "cardinalidad_origen": datos.cardinalidad_origen,
            "cardinalidad_destino": datos.cardinalidad_destino,
            "ui": {"vertices": []},
        }
        estado["relaciones"] = {**estado["relaciones"], relacion_id: relacion}

        await self._guardar_estado(proyecto, estado)
        return relacion

    async def eliminar_relacion(self, proyecto_id: int, datos: EliminarRelacion) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        if datos.relacion_id not in estado["relaciones"]:
            raise NotFoundError("Relación no encontrada")

        relaciones = dict(estado["relaciones"])
        del relaciones[datos.relacion_id]
        estado["relaciones"] = relaciones

        await self._guardar_estado(proyecto, estado)
        return {"relacion_id": datos.relacion_id}

    async def modificar_ui(self, proyecto_id: int, datos: ModificarUI) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None:
            raise NotFoundError("Clase no encontrada")

        ui = dict(clase["ui"])
        if datos.x is not None:
            ui["x"] = datos.x
        if datos.y is not None:
            ui["y"] = datos.y
        if datos.ancho is not None:
            ui["ancho"] = datos.ancho
        if datos.color is not None:
            ui["color"] = datos.color

        clase = {**clase, "ui": ui}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "ui": ui}

    async def alinear_nodos(self, proyecto_id: int, datos: AlinearNodos) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clases = dict(estado["clases"])
        for pos in datos.posiciones:
            clase = clases.get(pos.clase_id)
            if clase is None:
                raise NotFoundError(f"Clase {pos.clase_id} no encontrada")
            clases[pos.clase_id] = {**clase, "ui": {**clase["ui"], "x": pos.x, "y": pos.y}}
        estado["clases"] = clases

        await self._guardar_estado(proyecto, estado)
        return {"posiciones": [p.model_dump() for p in datos.posiciones]}
