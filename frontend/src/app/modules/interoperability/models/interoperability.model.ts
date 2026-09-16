export type BaseDatosDestino = 'POSTGRESQL' | 'MYSQL' | 'H2';

export interface ConfiguracionTranspilacion {
  configurado: boolean;
  group_id: string;
  artifact_id: string;
  java_version: string;
  spring_boot_version: string;
  base_datos: BaseDatosDestino;
}
