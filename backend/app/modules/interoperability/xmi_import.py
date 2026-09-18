import re
import uuid
from xml.etree.ElementTree import Element, ParseError, fromstring

from app.core.exceptions import AppException
from app.modules.interoperability.xmi_export import NS_XMI

_GEOMETRIA_RE = re.compile(r"Left=(-?\d+);Top=(-?\d+);")

_VISIBILIDAD_DESDE_XMI = {
    "public": "PUBLICO",
    "private": "PRIVADO",
    "protected": "PROTEGIDO",
    "package": "PAQUETE",
}

_AGREGACION_DESDE_XMI = {
    "shared": "AGREGACION",
    "composite": "COMPOSICION",
}

_ANCHO_MINIMO_CLASE = 90


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _tipo_xmi(el: Element) -> str | None:
    return el.get(_q(NS_XMI, "type"))


def _id_xmi(el: Element) -> str | None:
    return el.get(_q(NS_XMI, "id"))


def _idref(el: Element) -> str | None:
    return el.get(_q(NS_XMI, "idref"))


def _leer_cardinalidad(extremo: Element) -> str | None:
    lower = extremo.find("lowerValue")
    upper = extremo.find("upperValue")
    if lower is None or upper is None:
        return None
    inferior = lower.get("value")
    superior = upper.get("value")
    if inferior is None or superior is None:
        return None
    # "-1" es la convencion UML/EA para "sin limite" (LiteralUnlimitedNatural), no
    # un numero literal
    inferior = "*" if inferior == "-1" else inferior
    superior = "*" if superior == "-1" else superior
    return inferior if inferior == superior else f"{inferior}..{superior}"


def _leer_posiciones_diagrama(raiz: Element) -> dict[str, tuple[int, int]]:
    """Si el archivo trae un bloque xmi:Extension con diagrama (el nuestro, o uno
    nativo de EA), se puede reaprovechar la posicion de cada clase en vez de
    forzar una cuadricula. "subject" en cada <element> del diagrama apunta al
    mismo xmi:id que la clase declara en su packagedElement, en ambos casos."""
    posiciones: dict[str, tuple[int, int]] = {}
    for el in raiz.iter("element"):
        geometria = el.get("geometry")
        referencia = el.get("subject")
        if not geometria or not referencia:
            continue
        coincidencia = _GEOMETRIA_RE.match(geometria)
        if coincidencia:
            posiciones[referencia] = (int(coincidencia.group(1)), int(coincidencia.group(2)))
    return posiciones


def _leer_multiplicidades_conectores(raiz: Element) -> dict[str, dict[str, str]]:
    """El bloque xmi:Extension guarda en cada <connector> el texto de multiplicidad
    que EA realmente muestra en el diagrama (<source>/<target><type multiplicity=..>),
    y no siempre coincide con lo reconstruible desde lowerValue/upperValue del
    modelo UML: por ejemplo "1.." y "1..*" se guardan igual a nivel de modelo
    (upperValue=-1 en ambos) pero EA los distingue en el conector. Se indexa por
    el xmi:id de la relacion y luego por el xmi:id de cada clase (no por
    posicion), para poder aplicarlo sin importar el orden de los extremos."""
    resultado: dict[str, dict[str, str]] = {}
    for conector in raiz.iter("connector"):
        conector_id = _idref(conector)
        if not conector_id:
            continue
        entrada: dict[str, str] = {}
        for extremo_tag in ("source", "target"):
            extremo_el = conector.find(extremo_tag)
            if extremo_el is None:
                continue
            clase_ref = _idref(extremo_el)
            tipo_el = extremo_el.find("type")
            multiplicidad = tipo_el.get("multiplicity") if tipo_el is not None else None
            if clase_ref and multiplicidad:
                entrada[clase_ref] = multiplicidad
        if entrada:
            resultado[conector_id] = entrada
    return resultado


def _es_nuestro_archivo(raiz: Element) -> bool:
    """True si el paquete raiz usa nuestro propio id ("pkg_<id>"). EA jamas
    conserva esa cadena: al abrir o reexportar cualquier archivo reescribe todos
    los ids con su propia convencion (EAPK_/EAID_...). Sirve para distinguir un
    archivo que generamos nosotros (puro o "para EA") de uno realmente nativo de
    EA, que sigue una convencion propia y opuesta para marcar el extremo "todo"
    de una agregacion/composicion (confirmado con archivos reales de EA)."""
    return any(
        _tipo_xmi(el) == "uml:Package" and (_id_xmi(el) or "").startswith("pkg_")
        for el in raiz.iter("packagedElement")
    )


def importar_xmi(contenido: bytes) -> dict:
    """Reconstruye clases/relaciones a partir de un XMI 2.1/UML2 estandar (el mismo
    formato que produce construir_xmi con para_ea=False). Genera ids internos nuevos
    para cada elemento; los xmi:id del archivo solo se usan para resolver referencias
    (type/@idref, general, boundElement, client/supplier, memberEnd) durante el parseo."""
    try:
        raiz = fromstring(contenido)
    except ParseError as e:
        raise AppException(f"El archivo no es un XML válido: {e}") from e

    es_nuestro = _es_nuestro_archivo(raiz)
    tiene_extension = raiz.find(_q(NS_XMI, "Extension")) is not None
    # nuestro propio export "para EA" cruza a proposito cardinalidad/agregacion
    # entre los dos extremos de cada relacion, para que EA los muestre bien
    # DESPUES de reimportarlos (ver xmi_export.py::_emitir_extremos). Si ese
    # archivo se importa directo a nuestro sistema sin pasar por EA de verdad,
    # ese cruce nunca se deshace solo y hay que revertirlo a mano.
    invertir = es_nuestro and tiene_extension
    # un archivo realmente nativo de EA (nunca es nuestro) marca el extremo
    # "todo" de una agregacion/composicion al reves que nosotros
    es_ea_nativo = not es_nuestro
    multiplicidades_conectores = _leer_multiplicidades_conectores(raiz)

    nombres_tipo: dict[str, str] = {}
    for el in raiz.iter("packagedElement"):
        if _tipo_xmi(el) == "uml:PrimitiveType":
            id_el = _id_xmi(el)
            nombre = el.get("name")
            if id_el and nombre:
                nombres_tipo[id_el] = nombre

    def _tipo_de(propiedad: Element) -> str | None:
        # el tipo casi siempre va en un <type xmi:idref="..."> anidado, pero EA
        # nativo pone el tipo de los ownedParameter como atributo directo
        # (type="EAJava_double") en vez de como elemento hijo
        tipo_el = propiedad.find("type")
        if tipo_el is not None:
            ref = _idref(tipo_el)
            if ref:
                return nombres_tipo.get(ref)
        ref_directo = propiedad.get("type")
        return nombres_tipo.get(ref_directo) if ref_directo else None

    clases: dict[str, dict] = {}
    relaciones: dict[str, dict] = {}
    id_por_xmi: dict[str, str] = {}
    generalizaciones_pendientes: list[tuple[str, str]] = []
    bindings_pendientes: list[tuple[str, str]] = []

    def _nuevo_id() -> str:
        return str(uuid.uuid4())

    def _parsear_atributos_y_metodos(elemento_clase: Element) -> tuple[dict, dict]:
        atributos: dict[str, dict] = {}
        for orden, attr_el in enumerate(elemento_clase.findall("ownedAttribute")):
            # las que son extremos de asociacion (aggregation=...) no son atributos de negocio
            if attr_el.get("association"):
                continue
            aid = _nuevo_id()
            atributos[aid] = {
                "id": aid,
                "nombre": attr_el.get("name") or "",
                "tipo": _tipo_de(attr_el),
                "es_pk": attr_el.get("isID") == "true",
                "visibilidad": _VISIBILIDAD_DESDE_XMI.get(attr_el.get("visibility") or "", "PRIVADO"),
                "orden": orden,
            }

        metodos: dict[str, dict] = {}
        for orden, op_el in enumerate(elemento_clase.findall("ownedOperation")):
            parametros = []
            tipo_retorno = None
            for param_el in op_el.findall("ownedParameter"):
                if param_el.get("direction") == "return":
                    tipo_retorno = _tipo_de(param_el)
                else:
                    parametros.append({"nombre": param_el.get("name") or "", "tipo": _tipo_de(param_el)})
            mid = _nuevo_id()
            metodos[mid] = {
                "id": mid,
                "nombre": op_el.get("name") or "",
                "tipo_retorno": tipo_retorno,
                "parametros": parametros,
                "visibilidad": _VISIBILIDAD_DESDE_XMI.get(op_el.get("visibility") or "", "PUBLICO"),
                "orden": orden,
            }

        return atributos, metodos

    def _registrar_clase(elemento: Element) -> None:
        xmi_id = _id_xmi(elemento)
        interno_id = _nuevo_id()
        if xmi_id:
            id_por_xmi[xmi_id] = interno_id

        atributos, metodos = _parsear_atributos_y_metodos(elemento)
        clases[interno_id] = {
            "id": interno_id,
            "nombre": elemento.get("name") or "Clase",
            "atributos": atributos,
            "metodos": metodos,
            "ui": {"x": 0, "y": 0, "ancho": _ANCHO_MINIMO_CLASE, "color": "#e3f2fd"},
        }

        for gen_el in elemento.findall("generalization"):
            general_ref = gen_el.get("general")
            if general_ref and xmi_id:
                generalizaciones_pendientes.append((xmi_id, general_ref))
        for bind_el in elemento.findall("templateBinding"):
            bound_ref = bind_el.get("boundElement")
            if bound_ref and xmi_id:
                bindings_pendientes.append((xmi_id, bound_ref))

    # 1a pasada: registrar todas las clases (para que las referencias hacia
    # adelante o hacia atras entre ellas se puedan resolver despues). Solo se
    # considera "packagedElement": el bloque xmi:Extension de EA repite un
    # <element xmi:type="uml:Class" xmi:idref="..."> por cada clase como resumen
    # (no es una declaracion), y con el mismo xmi:type se duplicaria todo.
    for el in raiz.iter("packagedElement"):
        if _tipo_xmi(el) in ("uml:Class", "uml:AssociationClass"):
            _registrar_clase(el)

    # indice de todo "extremo de relacion" por su xmi:id: normalmente son ownedEnd
    # anidados en la propia Association, pero EA a veces guarda un extremo como
    # ownedAttribute de la CLASE (con association="..." apuntando de vuelta) en vez
    # de como ownedEnd - sin este indice, memberEnd no lo encuentra y la relacion
    # entera se pierde
    propiedades_por_id: dict[str, Element] = {}
    for el in raiz.iter():
        if el.tag == "ownedEnd" or (el.tag == "ownedAttribute" and el.get("association")):
            pid = _id_xmi(el)
            if pid:
                propiedades_por_id[pid] = el

    def _procesar_extremos(el: Element) -> tuple[str, dict] | None:
        refs = [_idref(me) for me in el.findall("memberEnd")]
        extremos = [propiedades_por_id[r] for r in refs if r and r in propiedades_por_id]
        if len(extremos) < 2:
            extremos = el.findall("ownedEnd")  # respaldo si no hay memberEnd explicito
        if len(extremos) < 2:
            return None
        e1, e2 = extremos[0], extremos[1]
        tipo1, tipo2 = e1.find("type"), e2.find("type")
        xmi1 = _idref(tipo1) if tipo1 is not None else None
        xmi2 = _idref(tipo2) if tipo2 is not None else None
        id1 = id_por_xmi.get(xmi1 or "")
        id2 = id_por_xmi.get(xmi2 or "")
        if not id1 or not id2:
            return None

        agg1 = e1.get("aggregation", "none")
        agg2 = e2.get("aggregation", "none")

        if invertir:
            # este archivo es nuestro propio export "para EA" sin pasar todavia por
            # EA de verdad: la CLASE de cada extremo va siempre en su posicion
            # natural (e1=origen, e2=destino), pero cardinalidad/agregacion estan
            # cruzadas a proposito - se deshace el cruce leyendolas cambiadas
            origen_id, destino_id = id1, id2
            origen_prop, destino_prop = e2, e1
            agregacion = agg1 if agg1 != "none" else agg2
        elif es_ea_nativo:
            # EA nativo marca como "agregacion/composicion" el extremo que
            # representa el ORIGEN (el "todo"), al reves que nuestro propio
            # exportador - confirmado contra archivos reales exportados de EA
            if agg1 != "none":
                origen_id, destino_id, origen_prop, destino_prop, agregacion = id1, id2, e1, e2, agg1
            elif agg2 != "none":
                origen_id, destino_id, origen_prop, destino_prop, agregacion = id2, id1, e2, e1, agg2
            else:
                origen_id, destino_id, origen_prop, destino_prop, agregacion = id1, id2, e1, e2, "none"
        # el extremo que SI trae la agregacion es "destino" (igual que hace nuestro
        # propio exportador: agg_destino=valor, agg_origen="none"), para que el
        # rombo termine del lado correcto en el lienzo
        elif agg1 != "none":
            origen_id, destino_id, origen_prop, destino_prop, agregacion = id2, id1, e2, e1, agg1
        elif agg2 != "none":
            origen_id, destino_id, origen_prop, destino_prop, agregacion = id1, id2, e1, e2, agg2
        else:
            origen_id, destino_id, origen_prop, destino_prop, agregacion = id1, id2, e1, e2, "none"

        cardinalidad_origen = _leer_cardinalidad(origen_prop)
        cardinalidad_destino = _leer_cardinalidad(destino_prop)

        # el conector de la Extension EA (si el archivo lo trae) tiene el texto
        # exacto que EA muestra, y puede distinguir casos que a nivel de modelo
        # UML quedan identicos (ej. "1.." vs "1..*", ambos con upperValue=-1).
        # Se aplica por identidad de clase, nunca por posicion. Solo para
        # archivos realmente nativos de EA: en nuestro propio export "para EA"
        # ese mismo conector trae la multiplicidad cruzada a proposito (igual
        # que el modelo UML), y el "invertir" de arriba ya la descruza bien.
        relacion_xmi_id = _id_xmi(el)
        overrides = multiplicidades_conectores.get(relacion_xmi_id or "") if es_ea_nativo else None
        if overrides:
            origen_xmi = xmi1 if origen_id == id1 else xmi2
            destino_xmi = xmi2 if origen_id == id1 else xmi1
            if origen_xmi in overrides:
                cardinalidad_origen = overrides[origen_xmi]
            if destino_xmi in overrides:
                cardinalidad_destino = overrides[destino_xmi]

        rid = _nuevo_id()
        return rid, {
            "id": rid,
            "origen_id": origen_id,
            "destino_id": destino_id,
            "tipo": _AGREGACION_DESDE_XMI.get(agregacion, "ASOCIACION"),
            "cardinalidad_origen": cardinalidad_origen,
            "cardinalidad_destino": cardinalidad_destino,
            # "name" es una etiqueta real solo en uml:Association; en
            # uml:AssociationClass es el nombre de la CLASE asociada (ej. "Class7"),
            # no una etiqueta de la linea
            "etiqueta": el.get("name") if _tipo_xmi(el) == "uml:Association" else None,
            "clase_asociada_id": None,
            "ui": {"vertices": []},
        }

    # 2a pasada: asociaciones, clases de asociacion y realizaciones (top-level)
    for el in raiz.iter("packagedElement"):
        tipo = _tipo_xmi(el)
        if tipo == "uml:Association":
            resultado = _procesar_extremos(el)
            if resultado:
                rid, datos = resultado
                relaciones[rid] = datos
        elif tipo == "uml:AssociationClass":
            resultado = _procesar_extremos(el)
            if resultado:
                rid, datos = resultado
                xmi_id = _id_xmi(el)
                datos["clase_asociada_id"] = id_por_xmi.get(xmi_id or "")
                relaciones[rid] = datos
        elif tipo == "uml:Realization":
            client_ref, supplier_ref = el.get("client"), el.get("supplier")
            origen_id = id_por_xmi.get(client_ref or "")
            destino_id = id_por_xmi.get(supplier_ref or "")
            if origen_id and destino_id:
                rid = _nuevo_id()
                relaciones[rid] = {
                    "id": rid,
                    "origen_id": origen_id,
                    "destino_id": destino_id,
                    "tipo": "REALIZACION",
                    "cardinalidad_origen": None,
                    "cardinalidad_destino": None,
                    "etiqueta": None,
                    "clase_asociada_id": None,
                    "ui": {"vertices": []},
                }

    # generalizaciones (herencia) y template bindings, anidados dentro de cada clase
    for origen_xmi, general_xmi in generalizaciones_pendientes:
        origen_id = id_por_xmi.get(origen_xmi)
        destino_id = id_por_xmi.get(general_xmi)
        if origen_id and destino_id:
            rid = _nuevo_id()
            relaciones[rid] = {
                "id": rid,
                "origen_id": origen_id,
                "destino_id": destino_id,
                "tipo": "HERENCIA",
                "cardinalidad_origen": None,
                "cardinalidad_destino": None,
                "etiqueta": None,
                "clase_asociada_id": None,
                "ui": {"vertices": []},
            }
    for origen_xmi, bound_xmi in bindings_pendientes:
        origen_id = id_por_xmi.get(origen_xmi)
        destino_id = id_por_xmi.get(bound_xmi)
        if origen_id and destino_id:
            rid = _nuevo_id()
            relaciones[rid] = {
                "id": rid,
                "origen_id": origen_id,
                "destino_id": destino_id,
                "tipo": "TEMPLATE_BINDING",
                "cardinalidad_origen": None,
                "cardinalidad_destino": None,
                "etiqueta": None,
                "clase_asociada_id": None,
                "ui": {"vertices": []},
            }

    if not clases:
        raise AppException("El archivo no tiene ninguna clase UML reconocible")

    # el XMI puro (OMG) no trae posiciones - esas son del bloque propietario
    # xmi:Extension - pero si el archivo lo trae (nuestra exportacion para EA, o un
    # archivo nativo de EA), se reaprovechan; el resto cae a una cuadricula simple,
    # igual que "alinear" en el lienzo
    posiciones = _leer_posiciones_diagrama(raiz)
    sin_posicion: list[dict] = []
    for xmi_id, interno_id in id_por_xmi.items():
        clase = clases[interno_id]
        pos = posiciones.get(xmi_id)
        if pos:
            clase["ui"]["x"], clase["ui"]["y"] = pos
        else:
            sin_posicion.append(clase)

    for indice, clase in enumerate(sin_posicion):
        clase["ui"]["x"] = 80 + (indice % 4) * 260
        clase["ui"]["y"] = 80 + (indice // 4) * 220

    return {"clases": clases, "relaciones": relaciones}
