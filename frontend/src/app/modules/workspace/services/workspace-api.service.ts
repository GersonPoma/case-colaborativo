import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { EstadoLienzo } from '../../../core/models/lienzo.model';
import { Pagina } from '../../../core/models/pagina.model';
import {
  CambiarRolColaborador,
  CrearProyecto,
  EnviarMensaje,
  InvitarColaborador,
  ResponderInvitacion,
} from '../models/proyecto-api.model';
import {
  Colaborador,
  HistorialVersionResumen,
  InvitacionPendiente,
  MensajeChat,
  Proyecto,
  ProyectoConRol,
} from '../models/proyecto.model';

@Injectable({ providedIn: 'root' })
export class WorkspaceApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  private paginar(pagina: number, tamano: number): HttpParams {
    return new HttpParams().set('pagina', pagina).set('tamano', tamano);
  }

  crear(datos: CrearProyecto): Observable<Proyecto> {
    return this.http.post<Proyecto>(this.baseUrl, datos);
  }

  listarPropios(pagina = 1, tamano = 10): Observable<Pagina<Proyecto>> {
    return this.http.get<Pagina<Proyecto>>(`${this.baseUrl}/propios`, {
      params: this.paginar(pagina, tamano),
    });
  }

  listarColaboraciones(pagina = 1, tamano = 10): Observable<Pagina<ProyectoConRol>> {
    return this.http.get<Pagina<ProyectoConRol>>(`${this.baseUrl}/colaboraciones`, {
      params: this.paginar(pagina, tamano),
    });
  }

  obtener(id: number): Observable<Proyecto> {
    return this.http.get<Proyecto>(`${this.baseUrl}/${id}`);
  }

  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }

  listarColaboradores(id: number, pagina = 1, tamano = 10): Observable<Pagina<Colaborador>> {
    return this.http.get<Pagina<Colaborador>>(`${this.baseUrl}/${id}/colaboradores`, {
      params: this.paginar(pagina, tamano),
    });
  }

  invitarColaborador(id: number, datos: InvitarColaborador): Observable<Colaborador> {
    return this.http.post<Colaborador>(`${this.baseUrl}/${id}/colaboradores`, datos);
  }

  cambiarRolColaborador(
    id: number,
    idUsuario: number,
    datos: CambiarRolColaborador,
  ): Observable<Colaborador> {
    return this.http.patch<Colaborador>(
      `${this.baseUrl}/${id}/colaboradores/${idUsuario}`,
      datos,
    );
  }

  quitarColaborador(id: number, idUsuario: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}/colaboradores/${idUsuario}`);
  }

  listarInvitacionesPendientes(
    pagina = 1,
    tamano = 10,
  ): Observable<Pagina<InvitacionPendiente>> {
    return this.http.get<Pagina<InvitacionPendiente>>(`${this.baseUrl}/invitaciones`, {
      params: this.paginar(pagina, tamano),
    });
  }

  responderInvitacion(id: number, datos: ResponderInvitacion): Observable<Colaborador> {
    return this.http.post<Colaborador>(`${this.baseUrl}/${id}/invitacion/responder`, datos);
  }

  listarHistorial(
    id: number,
    pagina = 1,
    tamano = 10,
  ): Observable<Pagina<HistorialVersionResumen>> {
    return this.http.get<Pagina<HistorialVersionResumen>>(`${this.baseUrl}/${id}/historial`, {
      params: this.paginar(pagina, tamano),
    });
  }

  obtenerLienzoHistorial(id: number, historialId: number): Observable<EstadoLienzo> {
    return this.http.get<EstadoLienzo>(`${this.baseUrl}/${id}/historial/${historialId}/lienzo`);
  }

  crearVersionHistorial(id: number): Observable<HistorialVersionResumen> {
    return this.http.post<HistorialVersionResumen>(`${this.baseUrl}/${id}/historial`, {});
  }

  restaurarVersion(id: number, historialId: number): Observable<Proyecto> {
    return this.http.post<Proyecto>(
      `${this.baseUrl}/${id}/historial/${historialId}/restaurar`,
      {},
    );
  }

  listarMensajes(id: number, pagina = 1, tamano = 20): Observable<Pagina<MensajeChat>> {
    return this.http.get<Pagina<MensajeChat>>(`${this.baseUrl}/${id}/mensajes`, {
      params: this.paginar(pagina, tamano),
    });
  }

  enviarMensaje(id: number, datos: EnviarMensaje): Observable<MensajeChat> {
    return this.http.post<MensajeChat>(`${this.baseUrl}/${id}/mensajes`, datos);
  }
}
