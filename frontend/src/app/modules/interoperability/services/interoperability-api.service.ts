import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ConfigurarTranspilacion } from '../models/interoperability-api.model';
import { ConfiguracionTranspilacion } from '../models/interoperability.model';

@Injectable({ providedIn: 'root' })
export class InteroperabilidadApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  obtenerConfiguracionTranspilacion(proyectoId: number): Observable<ConfiguracionTranspilacion> {
    return this.http.get<ConfiguracionTranspilacion>(
      `${this.baseUrl}/${proyectoId}/transpilacion`,
    );
  }

  configurarTranspilacion(
    proyectoId: number,
    datos: ConfigurarTranspilacion,
  ): Observable<ConfiguracionTranspilacion> {
    return this.http.put<ConfiguracionTranspilacion>(
      `${this.baseUrl}/${proyectoId}/transpilacion`,
      datos,
    );
  }
}
