import uuid
from io import BytesIO
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent, register_namespace

NS_XMI = "http://schema.omg.org/spec/XMI/2.1"
NS_UML = "http://schema.omg.org/spec/UML/2.1"

register_namespace("xmi", NS_XMI)
register_namespace("uml", NS_UML)

VISIBILIDAD_XMI = {
    "PUBLICO": "public",
    "PRIVADO": "private",
    "PROTEGIDO": "protected",
    "PAQUETE": "package",
}

AGREGACION_XMI = {
    "COMPOSICION": "composite",
    "AGREGACION": "shared",
}

EA_SCOPE = {
    "PUBLICO": "Public",
    "PRIVADO": "Private",
    "PROTEGIDO": "Protected",
    "PAQUETE": "Package",
}

EA_TIPO_CONECTOR = {
    "ASOCIACION": "Association",
    "AGREGACION": "Aggregation",
    "COMPOSICION": "Aggregation",
    "HERENCIA": "Generalization",
    "REALIZACION": "Realisation",  # ortografia britanica: asi la espera EA, no "Realization"
    "TEMPLATE_BINDING": "TemplateBinding",
}


def _qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _parsear_cardinalidad(valor: str | None) -> tuple[str, str] | None:
    if not valor:
        return None
    valor = valor.strip()
    if not valor:
        return None
    if ".." in valor:
        inferior, superior = valor.split("..", 1)
    else:
        inferior = superior = valor
    inferior = "0" if inferior == "*" else inferior
    return inferior, superior


def _formato_multiplicidad_ea(valor: str | None) -> str | None:
    """EA no colapsa "1..1" a "1" leyendo lowerValue/upperValue del modelo UML: lee
    este string directo del atributo multiplicity del conector en su extension. Un
    "*" suelto se deja tal cual (asi lo escribe EA), no se expande a "0..*"."""
    if not valor:
        return None
    valor = valor.strip()
    if not valor:
        return None
    if valor == "*":
        return "*"
    if ".." in valor:
        inferior, superior = valor.split("..", 1)
        return inferior if inferior == superior else valor
    return valor


class _RegistroTipos:
    """Junta cada nombre de tipo distinto usado en atributos/métodos para declararlo
    una sola vez como uml:PrimitiveType y poder referenciarlo por id desde donde se use."""

    def __init__(self) -> None:
        self._ids: dict[str, str] = {}

    def id_de(self, tipo: str | None) -> str | None:
        if not tipo:
            return None
        if tipo not in self._ids:
            self._ids[tipo] = f"type_{len(self._ids) + 1}"
        return self._ids[tipo]

    def elementos(self) -> list[tuple[str, str]]:
        return list(self._ids.items())


def construir_xmi(
    clases: dict,
    relaciones: dict,
    nombre_proyecto: str,
    proyecto_id: int,
    para_ea: bool = False,
) -> bytes:
    """Genera el XMI del diagrama. Con para_ea=False es un XMI 2.1/UML2 estandar.
    Con para_ea=True agrega ademas el bloque propietario de Enterprise
    Architect (xmi:Documentation + xmi:Extension) para que, al importarlo, EA
    tambien dibuje el diagrama con las clases ya posicionadas."""
    tipos = _RegistroTipos()

    xmi = Element(_qn(NS_XMI, "XMI"), {_qn(NS_XMI, "version"): "2.1"})
    if para_ea:
        SubElement(
            xmi,
            _qn(NS_XMI, "Documentation"),
            {"exporter": "Enterprise Architect", "exporterVersion": "6.5"},
        )
    modelo = SubElement(
        xmi,
        _qn(NS_UML, "Model"),
        {
            _qn(NS_XMI, "type"): "uml:Model",
            "name": "EA_Model" if para_ea else nombre_proyecto,
            "visibility": "public",
        },
    )

    # EA solo reconoce el paquete como "owner" valido del diagrama; poner las clases
    # directo bajo uml:Model (sin un uml:Package explicito) hace que EA no encuentre
    # a que paquete pertenece el diagrama y descarte todo el bloque Extension.
    id_paquete = f"pkg_{proyecto_id}"
    paquete = SubElement(
        modelo,
        "packagedElement",
        {
            _qn(NS_XMI, "type"): "uml:Package",
            _qn(NS_XMI, "id"): id_paquete,
            "name": nombre_proyecto,
            "visibility": "public",
        },
    )

    # las relaciones con clase asociada se fusionan en un solo uml:AssociationClass,
    # asi que esa clase no se emite tambien como uml:Class suelta
    ids_clase_asociada = {
        r["clase_asociada_id"] for r in relaciones.values() if r.get("clase_asociada_id")
    }

    generalizaciones_por_clase: dict[str, list[dict]] = {}
    bindings_por_clase: dict[str, list[dict]] = {}
    for rel_id, rel in relaciones.items():
        if rel["tipo"] == "HERENCIA":
            generalizaciones_por_clase.setdefault(rel["origen_id"], []).append(
                {**rel, "id": rel_id}
            )
        elif rel["tipo"] == "TEMPLATE_BINDING":
            bindings_por_clase.setdefault(rel["origen_id"], []).append({**rel, "id": rel_id})

    for clase_id, clase in clases.items():
        if clase_id in ids_clase_asociada:
            continue
        _emitir_clase(
            paquete,
            clase,
            tipos,
            generalizaciones_por_clase.get(clase_id, []),
            bindings_por_clase.get(clase_id, []),
        )

    for rel_id, rel in relaciones.items():
        if rel.get("clase_asociada_id"):
            clase_asociada = clases.get(rel["clase_asociada_id"])
            if clase_asociada:
                _emitir_association_class(paquete, rel_id, rel, clase_asociada, tipos, para_ea)
            continue
        if rel["tipo"] in ("HERENCIA", "TEMPLATE_BINDING"):
            continue  # ya se emitio anidada dentro de la clase especifica
        if rel["tipo"] == "REALIZACION":
            SubElement(
                paquete,
                "packagedElement",
                {
                    _qn(NS_XMI, "type"): "uml:Realization",
                    _qn(NS_XMI, "id"): f"id_{rel_id}",
                    "client": f"id_{rel['origen_id']}",
                    "supplier": f"id_{rel['destino_id']}",
                },
            )
        else:
            _emitir_asociacion(paquete, rel_id, rel, tipos, para_ea)

    for tipo_nombre, tipo_id in tipos.elementos():
        SubElement(
            modelo,
            "packagedElement",
            {
                _qn(NS_XMI, "type"): "uml:PrimitiveType",
                _qn(NS_XMI, "id"): tipo_id,
                "name": tipo_nombre,
            },
        )

    if para_ea:
        _emitir_extension_ea(xmi, clases, relaciones, id_paquete, proyecto_id, nombre_proyecto)

    indent(xmi, space="  ")
    buffer = BytesIO()
    ElementTree(xmi).write(buffer, encoding="UTF-8", xml_declaration=True)
    return buffer.getvalue()


def _emitir_clase(
    modelo: Element,
    clase: dict,
    tipos: _RegistroTipos,
    generalizaciones: list[dict],
    bindings: list[dict] | None = None,
) -> Element:
    elemento = SubElement(
        modelo,
        "packagedElement",
        {
            _qn(NS_XMI, "type"): "uml:Class",
            _qn(NS_XMI, "id"): f"id_{clase['id']}",
            "name": clase["nombre"],
            "visibility": "public",
        },
    )
    for gen in sorted(generalizaciones, key=lambda r: r["destino_id"]):
        SubElement(
            elemento,
            "generalization",
            {
                _qn(NS_XMI, "type"): "uml:Generalization",
                _qn(NS_XMI, "id"): f"id_{gen['id']}",
                "general": f"id_{gen['destino_id']}",
            },
        )
    # uml:TemplateBinding va anidado en la clase que "usa" el template (origen),
    # referenciando la clase-template (destino) via boundElement. El id de
    # "signature" no resuelve a nada en nuestro modelo (no representamos
    # parametros de template), pero EA lo tolera igual en sus propios archivos.
    for binding in sorted(bindings or [], key=lambda r: r["destino_id"]):
        SubElement(
            elemento,
            "templateBinding",
            {
                _qn(NS_XMI, "type"): "uml:TemplateBinding",
                _qn(NS_XMI, "id"): f"id_{binding['id']}",
                "boundElement": f"id_{binding['destino_id']}",
                "signature": f"id_{binding['id']}_ts",
            },
        )
    _emitir_atributos_y_metodos(elemento, clase, tipos)
    return elemento


def _emitir_association_class(
    modelo: Element,
    rel_id: str,
    relacion: dict,
    clase_asociada: dict,
    tipos: _RegistroTipos,
    invertir_para_ea: bool = False,
) -> None:
    elemento = SubElement(
        modelo,
        "packagedElement",
        {
            _qn(NS_XMI, "type"): "uml:AssociationClass",
            _qn(NS_XMI, "id"): f"id_{clase_asociada['id']}",
            "name": clase_asociada["nombre"],
            "visibility": "public",
        },
    )
    _emitir_atributos_y_metodos(elemento, clase_asociada, tipos)
    _emitir_extremos(elemento, rel_id, relacion, invertir_para_ea)


def _emitir_atributos_y_metodos(elemento: Element, clase: dict, tipos: _RegistroTipos) -> None:
    atributos = sorted(clase["atributos"].values(), key=lambda a: a["orden"])
    for atributo in atributos:
        attrs = {
            _qn(NS_XMI, "type"): "uml:Property",
            _qn(NS_XMI, "id"): f"id_{atributo['id']}",
            "name": atributo["nombre"],
            "visibility": VISIBILIDAD_XMI.get(atributo["visibilidad"], "private"),
            "isStatic": "false",
            "isReadOnly": "false",
            "isDerived": "false",
            "isOrdered": "false",
            "isUnique": "true",
            "isDerivedUnion": "false",
        }
        if atributo.get("es_pk"):
            attrs["isID"] = "true"
        nodo = SubElement(elemento, "ownedAttribute", attrs)
        tipo_id = tipos.id_de(atributo.get("tipo"))
        if tipo_id:
            SubElement(nodo, "type", {_qn(NS_XMI, "idref"): tipo_id})

    metodos = sorted(clase["metodos"].values(), key=lambda m: m["orden"])
    for metodo in metodos:
        nodo = SubElement(
            elemento,
            "ownedOperation",
            {
                _qn(NS_XMI, "type"): "uml:Operation",
                _qn(NS_XMI, "id"): f"id_{metodo['id']}",
                "name": metodo["nombre"],
                "visibility": VISIBILIDAD_XMI.get(metodo["visibilidad"], "public"),
            },
        )
        # el parametro de retorno va AL FINAL (despues de los parametros reales):
        # asi lo ordena EA en sus propios archivos nativos, y si va primero su
        # importador se confunde y genera un parametro fantasma "DuplicateParam_1"
        for indice, parametro_datos in enumerate(metodo.get("parametros", [])):
            parametro = SubElement(
                nodo,
                "ownedParameter",
                {
                    _qn(NS_XMI, "id"): f"id_{metodo['id']}_p{indice}",
                    "name": parametro_datos["nombre"],
                    "direction": "in",
                },
            )
            tipo_param_id = tipos.id_de(parametro_datos.get("tipo"))
            if tipo_param_id:
                SubElement(parametro, "type", {_qn(NS_XMI, "idref"): tipo_param_id})

        tipo_retorno_id = tipos.id_de(metodo.get("tipo_retorno"))
        if tipo_retorno_id:
            # EA solo reconoce el parametro de retorno si trae name="return";
            # sin ese atributo su importador lo trata como incompleto y genera
            # un "DuplicateParam_1" fantasma para reemplazarlo
            parametro = SubElement(
                nodo,
                "ownedParameter",
                {_qn(NS_XMI, "id"): f"id_{metodo['id']}_return", "name": "return", "direction": "return"},
            )
            SubElement(parametro, "type", {_qn(NS_XMI, "idref"): tipo_retorno_id})


def _emitir_asociacion(
    modelo: Element, rel_id: str, relacion: dict, tipos: _RegistroTipos, invertir_para_ea: bool = False
) -> None:
    attrs = {_qn(NS_XMI, "type"): "uml:Association", _qn(NS_XMI, "id"): f"id_{rel_id}"}
    if relacion.get("etiqueta"):
        attrs["name"] = relacion["etiqueta"]
    elemento = SubElement(modelo, "packagedElement", attrs)
    _emitir_extremos(elemento, rel_id, relacion, invertir_para_ea)


def _emitir_extremos(
    elemento: Element, rel_id: str, relacion: dict, invertir_para_ea: bool = False
) -> None:
    # al reimportar, EA reasigna la clase de cada extremo por posicion (2do
    # ownedEnd pasa a ser "source") pero el valor (multiplicidad/agregacion) se
    # queda pegado a la posicion del documento, no viaja con la clase. Resultado:
    # clase y valor terminan desparejados. Para que el numero caiga en la clase
    # correcta despues de ese reordenamiento, se cruzan los valores entre los dos
    # extremos (no las clases, que se mandan siempre en su posicion natural).
    aggregation = AGREGACION_XMI.get(relacion["tipo"], "none")
    cardinalidad_origen = relacion.get("cardinalidad_origen")
    cardinalidad_destino = relacion.get("cardinalidad_destino")
    agg_origen, agg_destino = "none", aggregation
    if invertir_para_ea:
        cardinalidad_origen, cardinalidad_destino = cardinalidad_destino, cardinalidad_origen
        agg_origen, agg_destino = agg_destino, agg_origen

    id_src = f"id_{rel_id}_src"
    id_dst = f"id_{rel_id}_dst"
    SubElement(elemento, "memberEnd", {_qn(NS_XMI, "idref"): id_src})
    SubElement(elemento, "memberEnd", {_qn(NS_XMI, "idref"): id_dst})

    extremo_1 = SubElement(
        elemento,
        "ownedEnd",
        {
            _qn(NS_XMI, "type"): "uml:Property",
            _qn(NS_XMI, "id"): id_src,
            "association": f"id_{rel_id}",
            "aggregation": agg_origen,
        },
    )
    SubElement(extremo_1, "type", {_qn(NS_XMI, "idref"): f"id_{relacion['origen_id']}"})
    _emitir_multiplicidad(extremo_1, id_src, cardinalidad_origen)

    extremo_2 = SubElement(
        elemento,
        "ownedEnd",
        {
            _qn(NS_XMI, "type"): "uml:Property",
            _qn(NS_XMI, "id"): id_dst,
            "association": f"id_{rel_id}",
            "aggregation": agg_destino,
        },
    )
    SubElement(extremo_2, "type", {_qn(NS_XMI, "idref"): f"id_{relacion['destino_id']}"})
    _emitir_multiplicidad(extremo_2, id_dst, cardinalidad_destino)


def _emitir_multiplicidad(extremo: Element, id_extremo: str, valor: str | None) -> None:
    cardinalidad = _parsear_cardinalidad(valor)
    if not cardinalidad:
        return
    inferior, superior = cardinalidad
    SubElement(
        extremo,
        "lowerValue",
        {
            _qn(NS_XMI, "type"): "uml:LiteralInteger",
            _qn(NS_XMI, "id"): f"{id_extremo}_lower",
            "value": inferior,
        },
    )
    # EA solo colapsa la multiplicidad a un numero simple (ej. "1") cuando el limite
    # superior tambien es LiteralInteger; con LiteralUnlimitedNatural siempre muestra
    # el rango completo ("1..1"), asi que ese tipo se reserva para "*" (no acotado)
    tipo_superior = "uml:LiteralUnlimitedNatural" if superior == "*" else "uml:LiteralInteger"
    SubElement(
        extremo,
        "upperValue",
        {
            _qn(NS_XMI, "type"): tipo_superior,
            _qn(NS_XMI, "id"): f"{id_extremo}_upper",
            "value": superior,
        },
    )


def _alto_estimado(clase: dict) -> int:
    filas = len(clase.get("atributos", {})) + len(clase.get("metodos", {}))
    return 44 + max(filas, 1) * 16


# mismos valores que ANCHO_MINIMO_CLASE/PADDING_HORIZONTAL_CLASE del lienzo
# (x6-uml.util.ts), para que el ancho en EA se acerque al que se ve ahí
ANCHO_MINIMO_CLASE = 90
PADDING_HORIZONTAL_CLASE = 20


def _ancho_estimado(clase: dict) -> int:
    # sin canvas 2D disponible en el backend, se aproxima el ancho de cada texto
    # con la misma heuristica de respaldo que usa el frontend cuando measureText
    # no esta disponible (largo del texto * tamano de fuente * 0.6)
    textos = [(clase.get("nombre", ""), 12)]
    for atributo in clase.get("atributos", {}).values():
        sufijo = f": {atributo['tipo']}" if atributo.get("tipo") else ""
        textos.append((f"X {atributo.get('nombre', '')}{sufijo}", 10))
    for metodo in clase.get("metodos", {}).values():
        parametros = ", ".join(f"{p['nombre']}: {p['tipo']}" for p in metodo.get("parametros", []))
        retorno = metodo.get("tipo_retorno") or "void"
        textos.append((f"X {metodo.get('nombre', '')}({parametros}): {retorno}", 10))

    ancho_contenido = max((len(texto) * tamano * 0.6 for texto, tamano in textos), default=0)
    return max(ANCHO_MINIMO_CLASE, int(ancho_contenido) + PADDING_HORIZONTAL_CLASE)


def _emitir_extension_ea(
    xmi: Element,
    clases: dict,
    relaciones: dict,
    id_paquete: str,
    proyecto_id: int,
    nombre_proyecto: str,
) -> None:
    """Bloque propietario de Enterprise Architect (no forma parte del estandar XMI de
    OMG) para que, ademas de importar el modelo, EA dibuje un diagrama con las clases
    ya ubicadas segun la posicion que tienen en nuestro lienzo y las lineas de relacion
    trazadas entre ellas. Estructura reconstruida comparando contra un XMI real
    exportado por EA (no es documentacion oficial de Sparx): si EA lo rechaza o ignora
    parte de esto, es lo primero a revisar."""
    if not clases:
        return

    # relaciones con clase asociada: por ahora solo se posiciona la clase en el
    # diagrama, no se traza la linea (la fusion clase+asociacion de EA para este
    # caso no esta confirmada contra un ejemplo real)
    relaciones_dibujables = {
        rel_id: rel for rel_id, rel in relaciones.items() if not rel.get("clase_asociada_id")
    }

    extension = SubElement(
        xmi,
        _qn(NS_XMI, "Extension"),
        {"extender": "Enterprise Architect", "extenderID": "6.5"},
    )

    elementos = SubElement(extension, "elements")
    elemento_paquete = SubElement(
        elementos,
        "element",
        {
            _qn(NS_XMI, "idref"): id_paquete,
            _qn(NS_XMI, "type"): "uml:Package",
            "name": nombre_proyecto,
            "scope": "public",
        },
    )
    SubElement(elemento_paquete, "model", {"ea_localid": "1", "ea_eleType": "package"})

    for indice, (clase_id, clase) in enumerate(clases.items(), start=2):
        elemento = SubElement(
            elementos,
            "element",
            {
                _qn(NS_XMI, "idref"): f"id_{clase_id}",
                _qn(NS_XMI, "type"): "uml:Class",
                "name": clase["nombre"],
                "scope": "public",
            },
        )
        SubElement(
            elemento,
            "model",
            {
                "package": id_paquete,
                "tpos": "0",
                "ea_localid": str(indice),
                "ea_eleType": "element",
            },
        )

        # el orden de los atributos en el compartimento del diagrama lo toma EA de
        # aca (position), no del orden de los ownedAttribute en el modelo UML
        atributos = sorted(clase["atributos"].values(), key=lambda a: a["orden"])
        if atributos:
            bloque_atributos = SubElement(elemento, "attributes")
            for posicion, atributo in enumerate(atributos):
                attr_el = SubElement(
                    bloque_atributos,
                    "attribute",
                    {
                        _qn(NS_XMI, "idref"): f"id_{atributo['id']}",
                        "name": atributo["nombre"],
                        "scope": EA_SCOPE.get(atributo["visibilidad"], "Private"),
                    },
                )
                # EA lee el tipo mostrado en el compartimento de aqui, no del
                # ownedAttribute del modelo UML (confirmado con un archivo nativo de EA)
                props_attr = {"collection": "false", "static": "0", "duplicates": "0", "changeability": "changeable"}
                if atributo.get("tipo"):
                    props_attr = {"type": atributo["tipo"], **props_attr}
                SubElement(attr_el, "properties", props_attr)
                SubElement(attr_el, "containment", {"position": str(posicion)})

        # igual que con los atributos: sin este bloque EA no puede mostrar el
        # nombre de cada parametro junto a su tipo en el compartimento de metodos
        metodos = sorted(clase["metodos"].values(), key=lambda m: m["orden"])
        if metodos:
            bloque_operaciones = SubElement(elemento, "operations")
            for posicion, metodo in enumerate(metodos):
                op_el = SubElement(
                    bloque_operaciones,
                    "operation",
                    {
                        _qn(NS_XMI, "idref"): f"id_{metodo['id']}",
                        "name": metodo["nombre"],
                        "scope": EA_SCOPE.get(metodo["visibilidad"], "Public"),
                    },
                )
                SubElement(op_el, "properties", {"position": str(posicion)})
                # el tipo de retorno mostrado en el compartimento sale de aca (no del
                # ownedOperation del modelo UML), igual que el tipo de un atributo
                SubElement(
                    op_el,
                    "type",
                    {
                        "type": metodo.get("tipo_retorno") or "void",
                        "const": "false",
                        "static": "false",
                        "isAbstract": "false",
                        "synchronised": "0",
                        "concurrency": "Sequential",
                        "pure": "0",
                        "isQuery": "false",
                    },
                )
                parametros_el = SubElement(op_el, "parameters")

                # el retorno compartia "pos=0" con el primer parametro real: esa
                # colision de posicion hace que el importador de EA invente un
                # parametro fantasma "DuplicateParam_1". Se evita dandole al
                # retorno la posicion que sigue a todos los parametros reales
                # (y poniendolo al final, igual que a nivel de modelo UML)
                lista_parametros = metodo.get("parametros", [])
                for indice_param, parametro in enumerate(lista_parametros):
                    parametro_el = SubElement(
                        parametros_el,
                        "parameter",
                        {
                            _qn(NS_XMI, "idref"): f"id_{metodo['id']}_p{indice_param}",
                            "visibility": "public",
                        },
                    )
                    SubElement(
                        parametro_el,
                        "properties",
                        {"pos": str(indice_param), "type": parametro.get("tipo") or ""},
                    )

                parametro_retorno = SubElement(
                    parametros_el,
                    "parameter",
                    {_qn(NS_XMI, "idref"): f"id_{metodo['id']}_return", "visibility": "public"},
                )
                SubElement(
                    parametro_retorno,
                    "properties",
                    {"pos": str(len(lista_parametros)), "type": metodo.get("tipo_retorno") or "void"},
                )

    # ids cortos tipo EA (DUID) para poder referenciar, en la geometria de cada
    # conector del diagrama, las cajas de origen/destino ya colocadas
    duid_por_clase = {clase_id: uuid.uuid4().hex[:8].upper() for clase_id in clases}

    if relaciones_dibujables:
        conectores = SubElement(extension, "connectors")
        for rel_id, rel in relaciones_dibujables.items():
            origen = clases.get(rel["origen_id"])
            destino = clases.get(rel["destino_id"])
            if not origen or not destino:
                continue
            attrs_conector = {_qn(NS_XMI, "idref"): f"id_{rel_id}"}
            if rel.get("etiqueta") and rel["tipo"] != "TEMPLATE_BINDING":
                attrs_conector["name"] = rel["etiqueta"]
            conector = SubElement(conectores, "connector", attrs_conector)
            aggregation_destino = AGREGACION_XMI.get(rel["tipo"], "none")

            # mismo cruce de valores que en _emitir_extremos: las clases van en su
            # posicion natural (origen=source, destino=target), pero el valor que
            # EA termina mostrando en cada una es el del OTRO extremo, asi que se
            # manda ya cruzado para que despues de la reimportacion caiga bien.
            # Solo aplica a los tipos armados con ownedEnd (Herencia/Realizacion/
            # TemplateBinding usan client/supplier directo y no sufren esto).
            invertir = rel["tipo"] in ("ASOCIACION", "AGREGACION", "COMPOSICION")
            cardinalidad_origen = rel.get("cardinalidad_origen")
            cardinalidad_destino = rel.get("cardinalidad_destino")
            agg_origen, agg_destino = "none", aggregation_destino
            if invertir:
                cardinalidad_origen, cardinalidad_destino = cardinalidad_destino, cardinalidad_origen
                agg_origen, agg_destino = agg_destino, agg_origen

            origen_el = SubElement(conector, "source", {_qn(NS_XMI, "idref"): f"id_{rel['origen_id']}"})
            SubElement(origen_el, "model", {"type": "Class", "name": origen["nombre"]})
            attrs_tipo_origen = {"aggregation": agg_origen}
            multiplicidad_1 = _formato_multiplicidad_ea(cardinalidad_origen)
            if multiplicidad_1:
                attrs_tipo_origen["multiplicity"] = multiplicidad_1
            SubElement(origen_el, "type", attrs_tipo_origen)

            destino_el = SubElement(conector, "target", {_qn(NS_XMI, "idref"): f"id_{rel['destino_id']}"})
            SubElement(destino_el, "model", {"type": "Class", "name": destino["nombre"]})
            attrs_tipo_destino = {"aggregation": agg_destino}
            multiplicidad_2 = _formato_multiplicidad_ea(cardinalidad_destino)
            if multiplicidad_2:
                attrs_tipo_destino["multiplicity"] = multiplicidad_2
            SubElement(destino_el, "type", attrs_tipo_destino)

            # EA solo dibuja la decoracion (triangulo, diamante, flecha) cuando el
            # conector es direccional; con "Unspecified" lo pinta como linea plana
            direccion = (
                "Source -> Destination"
                if rel["tipo"] in ("HERENCIA", "REALIZACION", "TEMPLATE_BINDING", "AGREGACION", "COMPOSICION")
                else "Unspecified"
            )
            props_conector = {
                "ea_type": EA_TIPO_CONECTOR.get(rel["tipo"], "Association"),
                "direction": direccion,
            }
            if rel["tipo"] == "COMPOSICION":
                props_conector["subtype"] = "Strong"
            SubElement(conector, "properties", props_conector)

            # sin esto EA decide por su cuenta (aparentemente por posicion en el
            # diagrama, no por origen/destino) donde poner cada multiplicidad, y
            # puede terminar mostrandolas cruzadas entre los dos extremos
            attrs_labels = {}
            if multiplicidad_1:
                attrs_labels["lb"] = multiplicidad_1
            if multiplicidad_2:
                attrs_labels["rb"] = multiplicidad_2
            if rel["tipo"] == "TEMPLATE_BINDING":
                attrs_labels["mt"] = f"«bind» {rel['etiqueta']}" if rel.get("etiqueta") else "«bind»"
            elif rel.get("etiqueta"):
                attrs_labels["mt"] = rel["etiqueta"]
            if attrs_labels:
                SubElement(conector, "labels", attrs_labels)

    diagramas = SubElement(extension, "diagrams")
    diagrama = SubElement(diagramas, "diagram", {_qn(NS_XMI, "id"): f"dia_{proyecto_id}"})
    SubElement(diagrama, "model", {"package": id_paquete, "localID": "1", "owner": id_paquete})
    SubElement(diagrama, "properties", {"name": nombre_proyecto, "type": "Logical"})
    elementos_diagrama = SubElement(diagrama, "elements")

    # EA descarta en silencio la geometria de cualquier elemento con coordenada
    # negativa (cae a su posicion default en el origen), asi que se desplaza todo
    # el diagrama para que la esquina mas arriba/izquierda quede en 0,0 -
    # conserva las posiciones relativas entre clases
    xs = [int(clase.get("ui", {}).get("x", 0)) for clase in clases.values()]
    ys = [int(clase.get("ui", {}).get("y", 0)) for clase in clases.values()]
    desplazo_x = -min(xs) if xs and min(xs) < 0 else 0
    desplazo_y = -min(ys) if ys and min(ys) < 0 else 0

    for indice, (clase_id, clase) in enumerate(clases.items(), start=1):
        ui = clase.get("ui", {})
        x = int(ui.get("x", 0)) + desplazo_x
        y = int(ui.get("y", 0)) + desplazo_y
        ancho = _ancho_estimado(clase)
        alto = _alto_estimado(clase)
        SubElement(
            elementos_diagrama,
            "element",
            {
                "geometry": f"Left={x};Top={y};Right={x + ancho};Bottom={y + alto};",
                "subject": f"id_{clase_id}",
                "seqno": str(indice),
                "style": f"DUID={duid_por_clase[clase_id]};",
            },
        )

    for rel_id, rel in relaciones_dibujables.items():
        if rel["origen_id"] not in duid_por_clase or rel["destino_id"] not in duid_por_clase:
            continue
        SubElement(
            elementos_diagrama,
            "element",
            {
                "geometry": (
                    "SX=0;SY=0;EX=0;EY=0;EDGE=2;"
                    "$LLB=;LLT=;LMT=;LMB=;LRT=;LRB=;IRHS=;ILHS=;Path=;"
                ),
                "subject": f"id_{rel_id}",
                "style": (
                    f"Mode=3;EOID={duid_por_clase[rel['destino_id']]};"
                    f"SOID={duid_por_clase[rel['origen_id']]};"
                    "Color=-1;LWidth=0;Hidden=0;"
                ),
            },
        )
