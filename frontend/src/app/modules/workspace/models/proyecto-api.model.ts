import { RolColaborador } from './proyecto.model';

export interface CrearProyecto {
  nombre: string;
  descripcion?: string | null;
}

export interface InvitarColaborador {
  username: string;
  rol: RolColaborador;
}

export interface CambiarRolColaborador {
  rol: RolColaborador;
}

export interface EnviarMensaje {
  contenido: string;
}
