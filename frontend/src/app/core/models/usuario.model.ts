export interface Perfil {
  id: number;
  id_usuario: number;
  nombre: string;
  apellido: string;
  email: string;
  created_at: string;
  updated_at: string | null;
}

export interface Usuario {
  id: number;
  username: string;
  activo: boolean;
  created_at: string;
  perfil: Perfil | null;
}
