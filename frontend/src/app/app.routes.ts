import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./modules/landing/pages/home/home').then((m) => m.Home),
  },
  {
    path: 'editor',
    loadComponent: () => import('./modules/canvas/pages/editor/editor').then((m) => m.Editor),
  },
  {
    path: 'editor/:id',
    loadComponent: () => import('./modules/canvas/pages/editor/editor').then((m) => m.Editor),
    canActivate: [authGuard],
  },
  {
    path: 'proyectos',
    loadComponent: () =>
      import('./modules/workspace/pages/project-list/project-list').then((m) => m.ProjectList),
    canActivate: [authGuard],
  },
  {
    path: 'proyectos/:id',
    loadComponent: () =>
      import('./modules/workspace/pages/project-detail/project-detail').then(
        (m) => m.ProjectDetail,
      ),
    canActivate: [authGuard],
  },
  {
    path: 'proyectos/:id/colaboradores',
    loadComponent: () =>
      import('./modules/workspace/pages/collaborators/collaborators').then((m) => m.Collaborators),
    canActivate: [authGuard],
  },
  {
    path: 'iniciar-sesion',
    loadComponent: () => import('./modules/auth/pages/login/login').then((m) => m.Login),
  },
  {
    path: 'registro',
    loadComponent: () => import('./modules/auth/pages/register/register').then((m) => m.Register),
  },
  {
    path: 'recuperar-contrasena',
    loadComponent: () =>
      import('./modules/auth/pages/recover-password/recover-password').then(
        (m) => m.RecoverPassword,
      ),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
