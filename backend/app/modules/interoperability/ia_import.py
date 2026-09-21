import uuid

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config.settings import settings
from app.core.exceptions import AppException

_TIPOS_RELACION_VALIDOS = {
    "ASOCIACION",
    "AGREGACION",
    "COMPOSICION",
    "HERENCIA",
    "REALIZACION",
    "TEMPLATE_BINDING",
}
_VISIBILIDADES_VALIDAS = {"PUBLICO", "PRIVADO", "PROTEGIDO", "PAQUETE"}

_ANCHO_CLASE = 90
_SEPARACION_X = 260
_SEPARACION_Y = 220
_CLASES_POR_FILA = 4

_PROMPT = """\
Analiza la imagen de un diagrama de clases UML (puede estar dibujado a mano, \
en una pizarra o hecho con una herramienta de diagramas) y extrae su \
estructura completa.

Para cada clase, identifica:
- Su nombre.
- Sus atributos: nombre, tipo de dato (si no se especifica, dejalo vacio), \
si es la llave primaria (atributo "id" o marcado explicitamente), y su \
visibilidad segun el simbolo UML (+ = PUBLICO, - = PRIVADO, # = PROTEGIDO, \
~ = PAQUETE; si no hay simbolo, asumi PRIVADO).
- Sus metodos: nombre, tipo de retorno (vacio si no se especifica), \
visibilidad (mismo criterio que los atributos, pero si no hay simbolo \
asumi PUBLICO), y sus parametros (nombre y tipo de cada uno).

Para cada relacion entre dos clases, identifica:
- La clase origen y la clase destino. Si la relacion es de herencia, el \
origen es la subclase (la que hereda) y el destino es la superclase (la \
clase padre). Si es de realizacion, el origen es la clase que implementa y \
el destino es la interfaz. Para el resto de los tipos, el origen es la \
clase del extremo sin marca especial (sin rombo) y el destino es la clase \
del extremo con la marca (el rombo de agregacion/composicion), o el orden \
en que se dibujo la linea si no hay marca.
- El tipo de relacion: ASOCIACION (linea simple), AGREGACION (rombo hueco), \
COMPOSICION (rombo relleno), HERENCIA (triangulo hueco), REALIZACION \
(triangulo hueco con linea punteada), o TEMPLATE_BINDING.
- La cardinalidad en cada extremo, tal como aparece en el diagrama (ejemplos: \
"1", "0..1", "*", "1..*", "0..*"). Si no hay cardinalidad visible, dejala \
vacia.
- La etiqueta de la relacion (el nombre de la relacion, si tiene uno escrito \
junto a la linea). Si no tiene, dejala vacia.
- Si la relacion tiene una clase asociada: una clase que no se conecta \
directamente a ninguna de las dos clases de la relacion, sino a la propia \
linea que las une (a la mitad, o desde cualquier punto de esa linea, en vez \
de conectarse a una de las cajas de clase en los extremos). El estilo de \
esa conexion puede variar (linea punteada, solida, u otro), lo que la \
distingue es que conecta con la linea de la relacion y no con una clase. Si \
la relacion tiene una clase asociada asi, indica su nombre; si no, dejalo \
vacio.

Importante: cada linea fisicamente dibujada entre dos clases es una unica \
relacion, sin importar si tiene una clase asociada colgando de ella. No \
generes una relacion adicional para representar la clase asociada: la clase \
asociada va como un dato mas (clase_asociada) dentro de esa misma relacion, \
nunca como una relacion separada. Si entre el mismo par de clases hay mas de \
una linea dibujada, si te corresponde devolver una relacion por cada linea, \
pero nunca inventes una relacion que no tenga su propia linea dibujada en la \
imagen.

Devolve unicamente la estructura que se te pide, sin texto adicional. Si la \
imagen no tiene ninguna clase reconocible, devolve una lista de clases \
vacia.
"""


class _ParametroMetodoIA(BaseModel):
    nombre: str
    tipo: str | None = None


class _MetodoIA(BaseModel):
    nombre: str
    tipo_retorno: str | None = None
    visibilidad: str = "PUBLICO"
    parametros: list[_ParametroMetodoIA] = []


class _AtributoIA(BaseModel):
    nombre: str
    tipo: str | None = None
    es_pk: bool = False
    visibilidad: str = "PRIVADO"


class _ClaseIA(BaseModel):
    nombre: str
    atributos: list[_AtributoIA] = []
    metodos: list[_MetodoIA] = []


class _RelacionIA(BaseModel):
    origen: str
    destino: str
    tipo: str
    cardinalidad_origen: str | None = None
    cardinalidad_destino: str | None = None
    etiqueta: str | None = None
    clase_asociada: str | None = None


class _DiagramaIA(BaseModel):
    clases: list[_ClaseIA] = []
    relaciones: list[_RelacionIA] = []


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _visibilidad(valor: str | None, defecto: str) -> str:
    if valor and valor.strip().upper() in _VISIBILIDADES_VALIDAS:
        return valor.strip().upper()
    return defecto


def _tipo_relacion(valor: str) -> str:
    if valor and valor.strip().upper() in _TIPOS_RELACION_VALIDOS:
        return valor.strip().upper()
    return "ASOCIACION"


def _limpio(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def generar_diagrama_desde_imagen(contenido: bytes, mime_type: str) -> dict:
    """Envia la imagen a Gemini y devuelve {clases, relaciones} en el mismo
    formato que espera REEMPLAZAR_LIENZO (igual que xmi_import.importar_xmi):
    ids propios generados aca, los de Gemini (nombres) solo se usan como
    clave de resolucion para las relaciones."""
    if not settings.GEMINI_API_KEY_IMAGEN:
        raise AppException("No hay una API key de Gemini configurada en el servidor.")

    cliente = genai.Client(api_key=settings.GEMINI_API_KEY_IMAGEN)
    try:
        respuesta = cliente.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=contenido, mime_type=mime_type),
                _PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_DiagramaIA,
            ),
        )
    except errors.ServerError as exc:
        raise AppException(
            "El servicio de IA esta saturado en este momento. Probá de nuevo en unos minutos."
        ) from exc
    except errors.ClientError as exc:
        raise AppException(f"No se pudo generar el diagrama: {exc.message}") from exc

    diagrama: _DiagramaIA = respuesta.parsed
    if diagrama is None or not diagrama.clases:
        raise AppException("No se pudo reconocer ninguna clase en la imagen.")

    clases: dict[str, dict] = {}
    id_por_nombre: dict[str, str] = {}

    for indice, clase_ia in enumerate(diagrama.clases):
        clase_id = _nuevo_id()
        id_por_nombre[clase_ia.nombre.strip().lower()] = clase_id

        atributos = {}
        for orden, attr in enumerate(clase_ia.atributos):
            atributo_id = _nuevo_id()
            atributos[atributo_id] = {
                "id": atributo_id,
                "nombre": attr.nombre,
                "tipo": _limpio(attr.tipo),
                "es_pk": attr.es_pk,
                "visibilidad": _visibilidad(attr.visibilidad, "PRIVADO"),
                "orden": orden,
            }

        metodos = {}
        for orden, metodo in enumerate(clase_ia.metodos):
            metodo_id = _nuevo_id()
            metodos[metodo_id] = {
                "id": metodo_id,
                "nombre": metodo.nombre,
                "tipo_retorno": _limpio(metodo.tipo_retorno),
                "parametros": [
                    {"nombre": p.nombre, "tipo": _limpio(p.tipo)} for p in metodo.parametros
                ],
                "visibilidad": _visibilidad(metodo.visibilidad, "PUBLICO"),
                "orden": orden,
            }

        fila, columna = divmod(indice, _CLASES_POR_FILA)
        clases[clase_id] = {
            "id": clase_id,
            "nombre": clase_ia.nombre,
            "atributos": atributos,
            "metodos": metodos,
            "ui": {
                "x": 80 + columna * _SEPARACION_X,
                "y": 80 + fila * _SEPARACION_Y,
                "ancho": _ANCHO_CLASE,
                "color": "#e3f2fd",
            },
        }

    relaciones: dict[str, dict] = {}
    for relacion_ia in diagrama.relaciones:
        origen_id = id_por_nombre.get(relacion_ia.origen.strip().lower())
        destino_id = id_por_nombre.get(relacion_ia.destino.strip().lower())
        if not origen_id or not destino_id:
            continue  # la IA menciono una clase que no llego a reconocer aparte
        clase_asociada_id = None
        if relacion_ia.clase_asociada:
            clase_asociada_id = id_por_nombre.get(relacion_ia.clase_asociada.strip().lower())
        relacion_id = _nuevo_id()
        relaciones[relacion_id] = {
            "id": relacion_id,
            "origen_id": origen_id,
            "destino_id": destino_id,
            "tipo": _tipo_relacion(relacion_ia.tipo),
            "cardinalidad_origen": _limpio(relacion_ia.cardinalidad_origen),
            "cardinalidad_destino": _limpio(relacion_ia.cardinalidad_destino),
            "etiqueta": _limpio(relacion_ia.etiqueta),
            "clase_asociada_id": clase_asociada_id,
            "ui": {"vertices": []},
        }

    return {"clases": clases, "relaciones": relaciones}
