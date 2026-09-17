import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.canvas.schema import (
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
    GuardarLienzo,
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

        # recarga por si otro usuario conectado al mismo proyecto guardó cambios
        await self.db.refresh(proyecto)

        actual = proyecto.estado_lienzo
        if actual:
            # copia superficial: para que SQLAlchemy detecte el cambio hace falta
            # reasignar un objeto nuevo, mutar el dict existente in-place no se persiste
            estado = dict(actual)
            # compatibilidad con clases guardadas antes de que existiera "metodos"
            estado["clases"] = {
                cid: {"metodos": {}, **c} for cid, c in estado["clases"].items()
            }
        else:
            estado = {"diagrama_id": str(proyecto.id), "clases": {}, "relaciones": {}}

        return proyecto, estado

    async def _guardar_estado(self, proyecto: Proyecto, estado: dict) -> None:
        proyecto.estado_lienzo = estado
        await self.db.commit()

    async def obtener_lienzo(self, proyecto_id: int) -> dict:
        _, estado = await self._obtener_estado(proyecto_id)
        return estado

    async def guardar_lienzo(self, proyecto_id: int, datos: GuardarLienzo) -> dict:
        proyecto = await self.proyecto_repository.get_by_id(proyecto_id)
        if proyecto is None:
            raise NotFoundError("Proyecto no encontrado")

        estado = {
            "diagrama_id": str(proyecto.id),
            "clases": {cid: c.model_dump(mode="json") for cid, c in datos.clases.items()},
            "relaciones": {rid: r.model_dump(mode="json") for rid, r in datos.relaciones.items()},
        }
        await self._guardar_estado(proyecto, estado)
        return estado

    async def reemplazar_lienzo(self, proyecto_id: int, datos: GuardarLienzo) -> dict:
        """Usado al importar un XMI: reemplaza por completo clases y relaciones
        (mismo comportamiento que guardar_lienzo, con otro nombre de acción de
        websocket para que el frontend lo pueda distinguir si hace falta)."""
        return await self.guardar_lienzo(proyecto_id, datos)

    async def crear_clase(self, proyecto_id: int, datos: CrearClase) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase_id = str(uuid.uuid4())
        clase = {
            "id": clase_id,
            "nombre": datos.nombre,
            "atributos": {},
            "metodos": {},
            "ui": {"x": datos.x, "y": datos.y, "ancho": 90, "color": "#e3f2fd"},
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
            if r["origen_id"] != datos.clase_id
            and r["destino_id"] != datos.clase_id
            and r.get("clase_asociada_id") != datos.clase_id
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
            "visibilidad": datos.visibilidad.value,
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
            "visibilidad": datos.visibilidad.value,
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

    async def agregar_metodo(self, proyecto_id: int, datos: AgregarMetodo) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None:
            raise NotFoundError("Clase no encontrada")

        metodo_id = str(uuid.uuid4())
        metodo = {
            "id": metodo_id,
            "nombre": datos.nombre,
            "tipo_retorno": datos.tipo_retorno,
            "parametros": [p.model_dump() for p in datos.parametros],
            "visibilidad": datos.visibilidad.value,
            "orden": len(clase["metodos"]),
        }
        clase = {**clase, "metodos": {**clase["metodos"], metodo_id: metodo}}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "metodo": metodo}

    async def editar_metodo(self, proyecto_id: int, datos: EditarMetodo) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None or datos.metodo_id not in clase["metodos"]:
            raise NotFoundError("Método no encontrado")

        metodo_anterior = clase["metodos"][datos.metodo_id]
        metodo = {
            **metodo_anterior,
            "nombre": datos.nombre,
            "tipo_retorno": datos.tipo_retorno,
            "parametros": [p.model_dump() for p in datos.parametros],
            "visibilidad": datos.visibilidad.value,
        }
        clase = {**clase, "metodos": {**clase["metodos"], datos.metodo_id: metodo}}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "metodo": metodo}

    async def eliminar_metodo(self, proyecto_id: int, datos: EliminarMetodo) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        clase = estado["clases"].get(datos.clase_id)
        if clase is None or datos.metodo_id not in clase["metodos"]:
            raise NotFoundError("Método no encontrado")

        metodos = dict(clase["metodos"])
        del metodos[datos.metodo_id]
        clase = {**clase, "metodos": metodos}
        estado["clases"] = {**estado["clases"], datos.clase_id: clase}

        await self._guardar_estado(proyecto, estado)
        return {"clase_id": datos.clase_id, "metodo_id": datos.metodo_id}

    async def trazar_relacion(self, proyecto_id: int, datos: TrazarRelacion) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        if datos.origen_id not in estado["clases"] or datos.destino_id not in estado["clases"]:
            raise NotFoundError("La clase de origen o destino no existe")

        if datos.clase_asociada_id is not None and datos.clase_asociada_id not in estado["clases"]:
            raise NotFoundError("La clase asociada no existe")

        relacion_id = str(uuid.uuid4())
        relacion = {
            "id": relacion_id,
            "origen_id": datos.origen_id,
            "destino_id": datos.destino_id,
            "tipo": datos.tipo.value,
            "cardinalidad_origen": datos.cardinalidad_origen,
            "cardinalidad_destino": datos.cardinalidad_destino,
            "etiqueta": datos.etiqueta,
            "clase_asociada_id": datos.clase_asociada_id,
            "ui": {"vertices": []},
        }
        estado["relaciones"] = {**estado["relaciones"], relacion_id: relacion}

        await self._guardar_estado(proyecto, estado)
        return relacion

    async def editar_relacion(self, proyecto_id: int, datos: EditarRelacion) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        if datos.relacion_id not in estado["relaciones"]:
            raise NotFoundError("Relación no encontrada")

        if datos.clase_asociada_id is not None and datos.clase_asociada_id not in estado["clases"]:
            raise NotFoundError("La clase asociada no existe")

        relacion_anterior = estado["relaciones"][datos.relacion_id]
        relacion = {
            **relacion_anterior,
            "tipo": datos.tipo.value,
            "cardinalidad_origen": datos.cardinalidad_origen,
            "cardinalidad_destino": datos.cardinalidad_destino,
            "etiqueta": datos.etiqueta,
            "clase_asociada_id": datos.clase_asociada_id,
        }
        estado["relaciones"] = {**estado["relaciones"], datos.relacion_id: relacion}

        await self._guardar_estado(proyecto, estado)
        return relacion

    async def eliminar_relacion(self, proyecto_id: int, datos: EliminarRelacion) -> dict:
        proyecto, estado = await self._obtener_estado(proyecto_id)

        relacion = estado["relaciones"].get(datos.relacion_id)
        if relacion is None:
            raise NotFoundError("Relación no encontrada")

        relaciones = dict(estado["relaciones"])
        del relaciones[datos.relacion_id]

        # una clase asociada vive y muere junto con su relación (como en Enterprise
        # Architect): al borrar la relación se borra también esa clase, y con ella
        # cualquier otra relación que dependiera de esa clase.
        clase_asociada_id = relacion.get("clase_asociada_id")
        if clase_asociada_id and clase_asociada_id in estado["clases"]:
            clases = dict(estado["clases"])
            del clases[clase_asociada_id]
            estado["clases"] = clases

            relaciones = {
                rid: r
                for rid, r in relaciones.items()
                if r["origen_id"] != clase_asociada_id
                and r["destino_id"] != clase_asociada_id
                and r.get("clase_asociada_id") != clase_asociada_id
            }
        else:
            clase_asociada_id = None

        estado["relaciones"] = relaciones

        await self._guardar_estado(proyecto, estado)
        return {"relacion_id": datos.relacion_id, "clase_asociada_id": clase_asociada_id}

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
