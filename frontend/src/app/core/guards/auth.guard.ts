import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthApiService } from '../../modules/auth/services/auth-api.service';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const authApi = inject(AuthApiService);
  const router = inject(Router);

  if (!authService.isLoggedIn()) {
    return router.parseUrl('/iniciar-sesion');
  }

  if (authService.usuario()) {
    return true;
  }

  return authApi.obtenerUsuarioActual().pipe(
    map((usuario) => {
      authService.setUsuario(usuario);
      return true;
    }),
    catchError(() => {
      authService.logout();
      return of(router.parseUrl('/iniciar-sesion'));
    }),
  );
};
