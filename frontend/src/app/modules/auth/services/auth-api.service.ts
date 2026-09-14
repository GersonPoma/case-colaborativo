import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Usuario } from '../../../core/models/usuario.model';
import { IniciarSesion, RegistrarUsuario, TokenRespuesta } from '../models/auth-api.model';

@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/auth`;

  registrar(datos: RegistrarUsuario): Observable<Usuario> {
    return this.http.post<Usuario>(`${this.baseUrl}/register`, datos);
  }

  iniciarSesion(datos: IniciarSesion): Observable<TokenRespuesta> {
    return this.http.post<TokenRespuesta>(`${this.baseUrl}/login`, datos);
  }

  obtenerUsuarioActual(): Observable<Usuario> {
    return this.http.get<Usuario>(`${this.baseUrl}/me`);
  }

  recuperarContrasena(email: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/recover-password`, { email });
  }

  restablecerContrasena(token: string, password: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/reset-password`, { token, password });
  }
}
