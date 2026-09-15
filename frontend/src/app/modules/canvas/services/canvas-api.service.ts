import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { EstadoLienzo } from '../../../core/models/lienzo.model';

@Injectable({ providedIn: 'root' })
export class CanvasApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  obtenerLienzo(proyectoId: number): Observable<EstadoLienzo> {
    return this.http.get<EstadoLienzo>(`${this.baseUrl}/${proyectoId}/lienzo`);
  }
}
