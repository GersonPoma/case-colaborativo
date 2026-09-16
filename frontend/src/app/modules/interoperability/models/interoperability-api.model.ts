import { BaseDatosDestino } from './interoperability.model';

export interface ConfigurarTranspilacion {
  group_id: string;
  artifact_id: string;
  java_version: string;
  spring_boot_version: string;
  base_datos: BaseDatosDestino;
}
