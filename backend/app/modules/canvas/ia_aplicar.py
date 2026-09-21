from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.canvas.schema import (
    AccionCanvas,
    AgregarAtributo,
    AgregarMetodo,
    CrearClase,
    EditarAtributo,
    EditarClase,
    EditarMetodo,
    EditarRelacion,
    EliminarAtributo,
    EliminarClase,
    EliminarMetodo,
    EliminarRelacion,
    MensajeSaliente,
    ParametroMetodo,
    TipoRelacion,
    TrazarRelacion,
    Visibilidad,
)
from app.websocket.manager import manager

if TYPE_CHECKING:
    from app.modules.canvas.service import CanvasService


def _visibilidad(valor: str | None, defecto: Visibilidad) -> Visibilidad:
    try:
        return Visibilidad(valor)
    except ValueError:
        return defecto


def _tipo_relacion(valor: str | None) -> TipoRelacion:
    try:
        return TipoRelacion(valor)
    except ValueError:
        return TipoRelacion.ASOCIACION


def _buscar_atributo_id(clase: dict, nombre: str) -> str | None:
    return next((aid for aid, a in clase["atributos"].items() if a["nombre"] == nombre), None)


def _buscar_metodo_id(clase: dict, nombre: str) -> str | None:
    return next((mid for mid, m in clase["metodos"].items() if m["nombre"] == nombre), None)


def _buscar_relacion_id(estado: dict, origen_id: str, destino_id: str) -> str | None:
    return next(
        (
            rid
            for rid, r in estado["relaciones"].items()
            if {r["origen_id"], r["destino_id"]} == {origen_id, destino_id}
        ),
        None,
    )


async def aplicar_operaciones(
    canvas_service: CanvasService, proyecto_id: int, usuario_id: int, operaciones: list[dict]
) -> list[dict]:
    """Aplica, una por una, las operaciones que interpretó la IA sobre el
    lienzo real (resolviendo nombres a ids contra el estado actual) y
    difunde cada cambio por websocket, igual que si lo hubiera hecho un
    usuario editando a mano. Una operación que no se puede resolver
    (clase/atributo/relación inexistente) simplemente se descarta."""
    aplicadas: list[dict] = []

    for op in operaciones:
        estado = await canvas_service.obtener_lienzo(proyecto_id)
        nombre_a_clase_id = {c["nombre"]: c["id"] for c in estado["clases"].values()}

        accion = op.get("accion")
        resultado = None
        accion_canvas = None

        if accion == "CREAR_CLASE":
            if not op.get("clase") or op["clase"] in nombre_a_clase_id:
                continue
            resultado = await canvas_service.crear_clase(
                proyecto_id, CrearClase(nombre=op["clase"], x=200, y=200)
            )
            accion_canvas = AccionCanvas.CREAR_CLASE

        elif accion == "EDITAR_CLASE":
            clase_id = nombre_a_clase_id.get(op.get("clase") or "")
            if clase_id is None or not op.get("nombre"):
                continue
            resultado = await canvas_service.editar_clase(
                proyecto_id, EditarClase(clase_id=clase_id, nombre=op["nombre"])
            )
            accion_canvas = AccionCanvas.EDITAR_CLASE

        elif accion == "ELIMINAR_CLASE":
            clase_id = nombre_a_clase_id.get(op.get("clase") or "")
            if clase_id is None:
                continue
            resultado = await canvas_service.eliminar_clase(proyecto_id, EliminarClase(clase_id=clase_id))
            accion_canvas = AccionCanvas.ELIMINAR_CLASE

        elif accion == "AGREGAR_ATRIBUTO":
            clase_id = nombre_a_clase_id.get(op.get("clase") or "")
            if clase_id is None or not op.get("nombre"):
                continue
            resultado = await canvas_service.agregar_atributo(
                proyecto_id,
                AgregarAtributo(
                    clase_id=clase_id,
                    nombre=op["nombre"],
                    tipo=op.get("tipo_dato"),
                    es_pk=op.get("es_pk", False),
                    visibilidad=_visibilidad(op.get("visibilidad"), Visibilidad.PRIVADO),
                ),
            )
            accion_canvas = AccionCanvas.AGREGAR_ATRIBUTO

        elif accion == "EDITAR_ATRIBUTO":
            clase = estado["clases"].get(nombre_a_clase_id.get(op.get("clase") or "", ""))
            if clase is None or not op.get("atributo"):
                continue
            atributo_id = _buscar_atributo_id(clase, op["atributo"])
            if atributo_id is None:
                continue
            resultado = await canvas_service.editar_atributo(
                proyecto_id,
                EditarAtributo(
                    clase_id=clase["id"],
                    atributo_id=atributo_id,
                    nombre=op.get("nombre") or op["atributo"],
                    tipo=op.get("tipo_dato"),
                    es_pk=op.get("es_pk", False),
                    visibilidad=_visibilidad(op.get("visibilidad"), Visibilidad.PRIVADO),
                ),
            )
            accion_canvas = AccionCanvas.EDITAR_ATRIBUTO

        elif accion == "ELIMINAR_ATRIBUTO":
            clase = estado["clases"].get(nombre_a_clase_id.get(op.get("clase") or "", ""))
            if clase is None or not op.get("atributo"):
                continue
            atributo_id = _buscar_atributo_id(clase, op["atributo"])
            if atributo_id is None:
                continue
            resultado = await canvas_service.eliminar_atributo(
                proyecto_id, EliminarAtributo(clase_id=clase["id"], atributo_id=atributo_id)
            )
            accion_canvas = AccionCanvas.ELIMINAR_ATRIBUTO

        elif accion == "AGREGAR_METODO":
            clase_id = nombre_a_clase_id.get(op.get("clase") or "")
            if clase_id is None or not op.get("nombre"):
                continue
            resultado = await canvas_service.agregar_metodo(
                proyecto_id,
                AgregarMetodo(
                    clase_id=clase_id,
                    nombre=op["nombre"],
                    tipo_retorno=op.get("tipo_retorno"),
                    parametros=[ParametroMetodo(**p) for p in op.get("parametros", [])],
                    visibilidad=_visibilidad(op.get("visibilidad"), Visibilidad.PUBLICO),
                ),
            )
            accion_canvas = AccionCanvas.AGREGAR_METODO

        elif accion == "EDITAR_METODO":
            clase = estado["clases"].get(nombre_a_clase_id.get(op.get("clase") or "", ""))
            if clase is None or not op.get("metodo"):
                continue
            metodo_id = _buscar_metodo_id(clase, op["metodo"])
            if metodo_id is None:
                continue
            resultado = await canvas_service.editar_metodo(
                proyecto_id,
                EditarMetodo(
                    clase_id=clase["id"],
                    metodo_id=metodo_id,
                    nombre=op.get("nombre") or op["metodo"],
                    tipo_retorno=op.get("tipo_retorno"),
                    parametros=[ParametroMetodo(**p) for p in op.get("parametros", [])],
                    visibilidad=_visibilidad(op.get("visibilidad"), Visibilidad.PUBLICO),
                ),
            )
            accion_canvas = AccionCanvas.EDITAR_METODO

        elif accion == "ELIMINAR_METODO":
            clase = estado["clases"].get(nombre_a_clase_id.get(op.get("clase") or "", ""))
            if clase is None or not op.get("metodo"):
                continue
            metodo_id = _buscar_metodo_id(clase, op["metodo"])
            if metodo_id is None:
                continue
            resultado = await canvas_service.eliminar_metodo(
                proyecto_id, EliminarMetodo(clase_id=clase["id"], metodo_id=metodo_id)
            )
            accion_canvas = AccionCanvas.ELIMINAR_METODO

        elif accion == "TRAZAR_RELACION":
            origen_id = nombre_a_clase_id.get(op.get("origen") or "")
            destino_id = nombre_a_clase_id.get(op.get("destino") or "")
            if origen_id is None or destino_id is None:
                continue
            resultado = await canvas_service.trazar_relacion(
                proyecto_id,
                TrazarRelacion(
                    origen_id=origen_id,
                    destino_id=destino_id,
                    tipo=_tipo_relacion(op.get("tipo_relacion")),
                    cardinalidad_origen=op.get("cardinalidad_origen"),
                    cardinalidad_destino=op.get("cardinalidad_destino"),
                    etiqueta=op.get("etiqueta"),
                ),
            )
            accion_canvas = AccionCanvas.TRAZAR_RELACION

        elif accion in ("EDITAR_RELACION", "ELIMINAR_RELACION"):
            origen_id = nombre_a_clase_id.get(op.get("origen") or "")
            destino_id = nombre_a_clase_id.get(op.get("destino") or "")
            if origen_id is None or destino_id is None:
                continue
            relacion_id = _buscar_relacion_id(estado, origen_id, destino_id)
            if relacion_id is None:
                continue

            if accion == "EDITAR_RELACION":
                resultado = await canvas_service.editar_relacion(
                    proyecto_id,
                    EditarRelacion(
                        relacion_id=relacion_id,
                        tipo=_tipo_relacion(op.get("tipo_relacion")),
                        cardinalidad_origen=op.get("cardinalidad_origen"),
                        cardinalidad_destino=op.get("cardinalidad_destino"),
                        etiqueta=op.get("etiqueta"),
                    ),
                )
                accion_canvas = AccionCanvas.EDITAR_RELACION
            else:
                resultado = await canvas_service.eliminar_relacion(
                    proyecto_id, EliminarRelacion(relacion_id=relacion_id)
                )
                accion_canvas = AccionCanvas.ELIMINAR_RELACION

        if resultado is not None and accion_canvas is not None:
            aplicadas.append({"accion": accion_canvas.value, "datos": resultado})
            salida = MensajeSaliente(accion=accion_canvas, datos=resultado, usuario_id=usuario_id)
            await manager.difundir(proyecto_id, salida.model_dump(mode="json"))

    return aplicadas
