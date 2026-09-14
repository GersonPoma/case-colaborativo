export type Visibilidad = 'PUBLICO' | 'PRIVADO' | 'PROTEGIDO';

export interface UIClase {
  x: number;
  y: number;
  ancho: number;
  color: string;
}

export interface Atributo {
  id: string;
  nombre: string;
  tipo: string;
  es_pk: boolean;
  visibilidad: Visibilidad;
  orden: number;
}

export interface ParametroMetodo {
  nombre: string;
  tipo: string;
}

export interface Metodo {
  id: string;
  nombre: string;
  tipo_retorno: string;
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
  tipo: string;
  cardinalidad_origen: string;
  cardinalidad_destino: string;
  ui: UIRelacion;
}

export interface EstadoLienzo {
  diagrama_id: string;
  clases: Record<string, Clase>;
  relaciones: Record<string, Relacion>;
}
