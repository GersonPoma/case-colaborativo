import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface RespuestaRefactorIa {
  respuesta: string;
  operaciones_aplicadas: number;
}

export interface RespuestaRefactorIaVoz extends RespuestaRefactorIa {
  texto: string;
}

@Injectable({ providedIn: 'root' })
export class IaService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  refactorizarPorTexto(proyectoId: number, texto: string): Observable<RespuestaRefactorIa> {
    return this.http.post<RespuestaRefactorIa>(`${this.baseUrl}/${proyectoId}/ia/texto`, { texto });
  }

  refactorizarPorVoz(proyectoId: number, audio: Blob): Observable<RespuestaRefactorIaVoz> {
    const formData = new FormData();
    formData.append('archivo', audio, 'audio.webm');
    return this.http.post<RespuestaRefactorIaVoz>(`${this.baseUrl}/${proyectoId}/ia/voz`, formData);
  }
}
