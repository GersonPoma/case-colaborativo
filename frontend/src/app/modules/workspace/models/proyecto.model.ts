export type RolColaborador = 'LECTOR' | 'EDITOR';
export type EstadoColaborador = 'PENDIENTE' | 'ACEPTADO' | 'RECHAZADO';

export interface Proyecto {
  id: number;
  nombre: string;
  descripcion: string | null;
  id_dueno: number;
  created_at: string;
  updated_at: string | null;
}

export interface ProyectoConRol {
  proyecto: Proyecto;
  rol: RolColaborador;
}

export interface UsuarioResumen {
  id: number;
  username: string;
}

export interface Colaborador {
  usuario: UsuarioResumen;
  rol: RolColaborador;
  estado: EstadoColaborador;
  unido_en: string;
}

export interface InvitacionPendiente {
  id_proyecto: number;
  proyecto: Proyecto;
  rol: RolColaborador;
  unido_en: string;
}

export interface HistorialVersionResumen {
  id: number;
  creado_por: number;
  fecha: string;
}

export interface MensajeChat {
  id: number;
  usuario: UsuarioResumen;
  contenido: string;
  fecha_envio: string;
}
