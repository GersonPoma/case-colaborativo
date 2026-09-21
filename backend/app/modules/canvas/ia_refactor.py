from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config.settings import settings
from app.core.exceptions import AppException

_ACCIONES_VALIDAS = {
    "CREAR_CLASE",
    "EDITAR_CLASE",
    "ELIMINAR_CLASE",
    "AGREGAR_ATRIBUTO",
    "EDITAR_ATRIBUTO",
    "ELIMINAR_ATRIBUTO",
    "AGREGAR_METODO",
    "EDITAR_METODO",
    "ELIMINAR_METODO",
    "TRAZAR_RELACION",
    "EDITAR_RELACION",
    "ELIMINAR_RELACION",
}

_PROMPT_BASE = """\
Sos un asistente que modifica un diagrama de clases UML a partir de \
instrucciones en lenguaje natural (escritas o transcriptas de voz).

Te paso el estado actual del diagrama (clases con sus atributos y metodos, y \
las relaciones entre clases) y una instruccion del usuario. Tu trabajo es \
devolver la lista de operaciones necesarias para cumplir esa instruccion.

Cada operacion tiene una "accion", que debe ser una de estas:
- CREAR_CLASE: crea una clase nueva. Usa "clase" (nombre de la clase nueva).
- EDITAR_CLASE: renombra una clase existente. Usa "clase" (nombre actual) y \
"nombre" (nombre nuevo).
- ELIMINAR_CLASE: elimina una clase existente (y sus atributos, metodos y \
relaciones). Usa "clase" (nombre actual).
- AGREGAR_ATRIBUTO: agrega un atributo nuevo a una clase existente. Usa \
"clase" (a que clase), "nombre" (nombre del atributo), "tipo_dato" (vacio si \
no se especifica), "es_pk" (true si es llave primaria) y "visibilidad" \
(PUBLICO, PRIVADO, PROTEGIDO o PAQUETE; PRIVADO si no se aclara).
- EDITAR_ATRIBUTO: modifica un atributo existente. Usa "clase", "atributo" \
(nombre ACTUAL del atributo a modificar), y los valores nuevos completos en \
"nombre", "tipo_dato", "es_pk" y "visibilidad" (repeti el valor actual en los \
campos que no cambian, los conoces por el estado del diagrama que te paso).
- ELIMINAR_ATRIBUTO: elimina un atributo existente. Usa "clase" y "atributo" \
(nombre actual).
- AGREGAR_METODO: agrega un metodo nuevo a una clase existente. Usa "clase", \
"nombre", "tipo_retorno" (vacio si no se especifica), "visibilidad" (PUBLICO \
si no se aclara) y "parametros" (lista de {{nombre, tipo}}).
- EDITAR_METODO: modifica un metodo existente. Usa "clase", "metodo" (nombre \
ACTUAL del metodo), y los valores nuevos completos en "nombre", \
"tipo_retorno", "visibilidad" y "parametros" (repeti lo que no cambia).
- ELIMINAR_METODO: elimina un metodo existente. Usa "clase" y "metodo" \
(nombre actual).
- TRAZAR_RELACION: crea una relacion nueva entre dos clases existentes. Usa \
"origen", "destino" (nombres de las clases), "tipo_relacion" (ASOCIACION, \
AGREGACION, COMPOSICION, HERENCIA, REALIZACION o TEMPLATE_BINDING; \
ASOCIACION si no se aclara), "cardinalidad_origen", "cardinalidad_destino" y \
"etiqueta" (vacios si no se especifican).
- EDITAR_RELACION: modifica una relacion existente entre dos clases. Usa \
"origen" y "destino" (para identificar cual relacion, si hay mas de una \
entre las mismas dos clases modifica la primera que corresponda al pedido), \
y los valores nuevos completos en "tipo_relacion", "cardinalidad_origen", \
"cardinalidad_destino" y "etiqueta".
- ELIMINAR_RELACION: elimina una relacion existente. Usa "origen" y \
"destino".

Reglas importantes:
- Los nombres de clases, atributos, metodos y relaciones que uses deben \
existir en el diagrama actual (salvo los que estes creando en esta misma \
instruccion), tal como estan escritos ahi.
- Si la instruccion pide algo sobre una clase/atributo/metodo que no existe \
en el diagrama y no lo estas creando, no generes una operacion para eso.
- Si la instruccion no requiere ningun cambio (pregunta, saludo, pedido \
ambiguo o imposible), devolve una lista de operaciones vacia.
- Generá las operaciones en el orden en que se deben aplicar (por ejemplo, \
primero CREAR_CLASE antes de agregarle atributos).
- Ademas de las operaciones, escribi en "respuesta" un mensaje corto (una o \
dos oraciones, en español, tono conversacional) confirmando que hiciste o \
explicando por que no hiciste nada.

Estado actual del diagrama:
{diagrama}

Instruccion del usuario:
{instruccion}
"""


class _ParametroMetodoIA(BaseModel):
    nombre: str
    tipo: str | None = None


class _OperacionIA(BaseModel):
    accion: str
    clase: str | None = None
    atributo: str | None = None
    metodo: str | None = None
    nombre: str | None = None
    tipo_dato: str | None = None
    es_pk: bool = False
    visibilidad: str = "PRIVADO"
    tipo_retorno: str | None = None
    parametros: list[_ParametroMetodoIA] = []
    origen: str | None = None
    destino: str | None = None
    tipo_relacion: str = "ASOCIACION"
    cardinalidad_origen: str | None = None
    cardinalidad_destino: str | None = None
    etiqueta: str | None = None


class _OperacionesIA(BaseModel):
    operaciones: list[_OperacionIA] = []
    respuesta: str = ""


def _describir_diagrama(estado_lienzo: dict) -> str:
    clases = estado_lienzo.get("clases", {})
    relaciones = estado_lienzo.get("relaciones", {})

    if not clases:
        return "(el diagrama esta vacio, no hay clases todavia)"

    lineas: list[str] = []
    for clase in clases.values():
        atributos = ", ".join(
            f"{a['nombre']}: {a.get('tipo') or 'sin tipo'}" + (" [PK]" if a.get("es_pk") else "")
            for a in sorted(clase.get("atributos", {}).values(), key=lambda a: a.get("orden", 0))
        )
        metodos = ", ".join(
            f"{m['nombre']}()" for m in sorted(clase.get("metodos", {}).values(), key=lambda m: m.get("orden", 0))
        )
        lineas.append(f"- Clase {clase['nombre']}: atributos=[{atributos}] metodos=[{metodos}]")

    nombre_por_id = {c["id"]: c["nombre"] for c in clases.values()}
    for relacion in relaciones.values():
        origen = nombre_por_id.get(relacion["origen_id"], "?")
        destino = nombre_por_id.get(relacion["destino_id"], "?")
        lineas.append(
            f"- Relacion {origen} ({relacion.get('cardinalidad_origen') or ''}) "
            f"--{relacion.get('tipo', 'ASOCIACION')}-- "
            f"({relacion.get('cardinalidad_destino') or ''}) {destino}"
        )

    return "\n".join(lineas)


def interpretar_instruccion(texto: str, estado_lienzo: dict) -> dict:
    if not settings.GEMINI_API_KEY_REFACTOR:
        raise AppException("No hay una API key de Gemini configurada para refactorizar.")

    prompt = _PROMPT_BASE.format(diagrama=_describir_diagrama(estado_lienzo), instruccion=texto)

    cliente = genai.Client(api_key=settings.GEMINI_API_KEY_REFACTOR)
    try:
        respuesta = cliente.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_OperacionesIA,
            ),
        )
    except errors.ServerError as exc:
        raise AppException(
            "El servicio de IA esta saturado en este momento. Probá de nuevo en unos minutos."
        ) from exc
    except errors.ClientError as exc:
        raise AppException(f"No se pudo interpretar la instrucción: {exc.message}") from exc

    resultado: _OperacionesIA | None = respuesta.parsed
    if resultado is None:
        raise AppException("La IA no devolvió una respuesta entendible.")

    operaciones = [
        op.model_dump() for op in resultado.operaciones if op.accion in _ACCIONES_VALIDAS
    ]
    return {"operaciones": operaciones, "respuesta": resultado.respuesta}
