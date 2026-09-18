export type Visibilidad = 'PUBLICO' | 'PRIVADO' | 'PROTEGIDO' | 'PAQUETE';
export type TipoRelacion =
  | 'ASOCIACION'
  | 'AGREGACION'
  | 'COMPOSICION'
  | 'HERENCIA'
  | 'REALIZACION'
  | 'TEMPLATE_BINDING';

export interface UIClase {
  x: number;
  y: number;
  ancho: number;
  color: string;
}

export interface Atributo {
  id: string;
  nombre: string;
  tipo: string | null;
  es_pk: boolean;
  visibilidad: Visibilidad;
  orden: number;
}

export interface ParametroMetodo {
  nombre: string;
  tipo: string | null;
}

export interface Metodo {
  id: string;
  nombre: string;
  tipo_retorno: string | null;
  parametros: ParametroMetodo[];
  visibilidad: Visibilidad;
  orden: number;
}

export interface Clase {
  id: string;
  nombre: string;
  atributos: Record<string, Atributo>;
  metodos: Record<string, Metodo>;
  ui: UIClase;
}

export interface UIRelacion {
  vertices: unknown[];
}

export interface Relacion {
  id: string;
  origen_id: string;
  destino_id: string;
  tipo: TipoRelacion;
  cardinalidad_origen: string | null;
  cardinalidad_destino: string | null;
  etiqueta: string | null;
  clase_asociada_id: string | null;
  ui: UIRelacion;
}

export interface EstadoLienzo {
  diagrama_id: string;
  clases: Record<string, Clase>;
  relaciones: Record<string, Relacion>;
}
