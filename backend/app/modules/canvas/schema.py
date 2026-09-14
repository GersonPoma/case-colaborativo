import enum

from pydantic import BaseModel


class AccionCanvas(str, enum.Enum):
    CREAR_CLASE = "CREAR_CLASE"
    EDITAR_CLASE = "EDITAR_CLASE"
    ELIMINAR_CLASE = "ELIMINAR_CLASE"
    AGREGAR_ATRIBUTO = "AGREGAR_ATRIBUTO"
    EDITAR_ATRIBUTO = "EDITAR_ATRIBUTO"
    ELIMINAR_ATRIBUTO = "ELIMINAR_ATRIBUTO"
    AGREGAR_METODO = "AGREGAR_METODO"
    EDITAR_METODO = "EDITAR_METODO"
    ELIMINAR_METODO = "ELIMINAR_METODO"
    TRAZAR_RELACION = "TRAZAR_RELACION"
    ELIMINAR_RELACION = "ELIMINAR_RELACION"
    MODIFICAR_UI = "MODIFICAR_UI"
    ALINEAR_NODOS = "ALINEAR_NODOS"


class Visibilidad(str, enum.Enum):
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    PROTEGIDO = "PROTEGIDO"


# estructura del estado_lienzo (para referencia / validación de salida)


class UIClase(BaseModel):
    x: float
    y: float
    ancho: float = 220
    color: str = "#e3f2fd"


class Atributo(BaseModel):
    id: str
    nombre: str
    tipo: str
    es_pk: bool = False
    visibilidad: Visibilidad = Visibilidad.PRIVADO
    orden: int = 0


class ParametroMetodo(BaseModel):
    nombre: str
    tipo: str


class Metodo(BaseModel):
    id: str
    nombre: str
    tipo_retorno: str
    parametros: list[ParametroMetodo] = []
    visibilidad: Visibilidad = Visibilidad.PUBLICO
    orden: int = 0


class Clase(BaseModel):
    id: str
    nombre: str
    atributos: dict[str, Atributo] = {}
    metodos: dict[str, Metodo] = {}
    ui: UIClase


class UIRelacion(BaseModel):
    vertices: list[dict] = []


class Relacion(BaseModel):
    id: str
    origen_id: str
    destino_id: str
    tipo: str
    cardinalidad_origen: str
    cardinalidad_destino: str
    ui: UIRelacion = UIRelacion()


class EstadoLienzo(BaseModel):
    diagrama_id: str
    clases: dict[str, Clase] = {}
    relaciones: dict[str, Relacion] = {}


# payloads de entrada por acción (van dentro de MensajeEntrante.datos)


class CrearClase(BaseModel):
    nombre: str
    x: float
    y: float


class EditarClase(BaseModel):
    clase_id: str
    nombre: str


class EliminarClase(BaseModel):
    clase_id: str


class AgregarAtributo(BaseModel):
    clase_id: str
    nombre: str
    tipo: str
    es_pk: bool = False
    visibilidad: Visibilidad = Visibilidad.PRIVADO


class EditarAtributo(BaseModel):
    clase_id: str
    atributo_id: str
    nombre: str
    tipo: str
    es_pk: bool = False
    visibilidad: Visibilidad = Visibilidad.PRIVADO


class EliminarAtributo(BaseModel):
    clase_id: str
    atributo_id: str


class AgregarMetodo(BaseModel):
    clase_id: str
    nombre: str
    tipo_retorno: str
    parametros: list[ParametroMetodo] = []
    visibilidad: Visibilidad = Visibilidad.PUBLICO


class EditarMetodo(BaseModel):
    clase_id: str
    metodo_id: str
    nombre: str
    tipo_retorno: str
    parametros: list[ParametroMetodo] = []
    visibilidad: Visibilidad = Visibilidad.PUBLICO


class EliminarMetodo(BaseModel):
    clase_id: str
    metodo_id: str


class TrazarRelacion(BaseModel):
    origen_id: str
    destino_id: str
    tipo: str
    cardinalidad_origen: str
    cardinalidad_destino: str


class EliminarRelacion(BaseModel):
    relacion_id: str


class ModificarUI(BaseModel):
    clase_id: str
    x: float | None = None
    y: float | None = None
    ancho: float | None = None
    color: str | None = None


class PosicionNodo(BaseModel):
    clase_id: str
    x: float
    y: float


class AlinearNodos(BaseModel):
    posiciones: list[PosicionNodo]


# envelope del WebSocket


class MensajeEntrante(BaseModel):
    accion: AccionCanvas
    datos: dict


class MensajeSaliente(BaseModel):
    accion: AccionCanvas
    datos: dict
    usuario_id: int


class MensajeError(BaseModel):
    error: str
