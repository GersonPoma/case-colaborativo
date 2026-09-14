export interface RegistrarUsuario {
  username: string;
  password: string;
  nombre: string;
  apellido: string;
  email: string;
}

export interface IniciarSesion {
  username: string;
  password: string;
}

export interface TokenRespuesta {
  access_token: string;
  token_type: string;
}
