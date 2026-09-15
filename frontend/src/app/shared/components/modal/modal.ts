import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-modal',
  imports: [],
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
})
export class Modal {
  readonly abierto = input(false);
  readonly ancho = input('360px');
  readonly cerrado = output<void>();

  cerrar(): void {
    this.cerrado.emit();
  }
}
