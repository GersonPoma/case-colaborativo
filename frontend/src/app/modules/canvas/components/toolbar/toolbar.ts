import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-toolbar',
  imports: [RouterLink],
  templateUrl: './toolbar.html',
  styleUrl: './toolbar.scss',
})
export class Toolbar {
  readonly conectado = input(false);
  readonly puedeEditar = input(false);
  readonly proyectoId = input.required<number>();
  readonly guardandoVersion = input(false);
  readonly puedeDeshacer = input(false);

  readonly guardarVersion = output<void>();
  readonly centrar = output<void>();
  readonly deshacer = output<void>();
}
