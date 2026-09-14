import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { Usuario } from '../models/usuario.model';

const TOKEN_KEY = 'case_auth_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  private readonly _token = signal<string | null>(
    this.isBrowser ? localStorage.getItem(TOKEN_KEY) : null,
  );
  private readonly _usuario = signal<Usuario | null>(null);

  readonly token = this._token.asReadonly();
  readonly usuario = this._usuario.asReadonly();
  readonly isLoggedIn = computed(() => this._token() !== null);

  setToken(token: string): void {
    if (this.isBrowser) {
      localStorage.setItem(TOKEN_KEY, token);
    }
    this._token.set(token);
  }

  setUsuario(usuario: Usuario | null): void {
    this._usuario.set(usuario);
  }

  logout(): void {
    if (this.isBrowser) {
      localStorage.removeItem(TOKEN_KEY);
    }
    this._token.set(null);
    this._usuario.set(null);
  }
}
