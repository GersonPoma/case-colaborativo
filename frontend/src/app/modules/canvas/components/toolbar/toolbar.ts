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
  readonly exportandoXmi = input(false);
  readonly exportandoXmiEa = input(false);
  readonly exportandoImagen = input(false);
  readonly importandoXmi = input(false);
  readonly generandoBackend = input(false);

  readonly guardarVersion = output<void>();
  readonly centrar = output<void>();
  readonly deshacer = output<void>();
  readonly exportarXmi = output<void>();
  readonly exportarXmiEa = output<void>();
  readonly exportarImagen = output<void>();
  readonly archivoXmiSeleccionado = output<File>();
  readonly generarBackend = output<void>();

  alSeleccionarArchivo(evento: Event): void {
    const input = evento.target as HTMLInputElement;
    const archivo = input.files?.[0];
    if (archivo) {
      this.archivoXmiSeleccionado.emit(archivo);
    }
    input.value = '';
  }
}
