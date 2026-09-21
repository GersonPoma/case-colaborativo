import { Clase, Relacion } from '../../../core/models/lienzo.model';

export type BaseDatosDestino = 'POSTGRESQL';

export interface ConfiguracionTranspilacion {
  configurado: boolean;
  group_id: string;
  artifact_id: string;
  java_version: string;
  spring_boot_version: string;
  base_datos: BaseDatosDestino;
}

export interface ImportarXmiResultado {
  clases: Record<string, Clase>;
  relaciones: Record<string, Relacion>;
}

export interface ImportarIaResultado {
  clases: Record<string, Clase>;
  relaciones: Record<string, Relacion>;
}
