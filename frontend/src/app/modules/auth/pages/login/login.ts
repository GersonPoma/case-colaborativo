import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { LucideEye, LucideEyeOff } from '@lucide/angular';
import { AuthService } from '../../../../core/services/auth.service';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { AuthApiService } from '../../services/auth-api.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink, LucideEye, LucideEyeOff],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApiService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly mostrarPassword = signal(false);

  readonly formulario = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3)]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.cargando.set(true);
    this.error.set(null);

    this.authApi.iniciarSesion(this.formulario.getRawValue()).subscribe({
      next: (respuesta) => {
        this.authService.setToken(respuesta.access_token);
        this.authApi.obtenerUsuarioActual().subscribe({
          next: (usuario) => this.authService.setUsuario(usuario),
          complete: () => {
            this.cargando.set(false);
            this.router.navigateByUrl('/proyectos');
          },
        });
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  alternarMostrarPassword(): void {
    this.mostrarPassword.update((valor) => !valor);
  }
}
