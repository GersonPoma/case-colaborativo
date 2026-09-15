import { Component, input, output } from '@angular/core';
import { TipoRelacion } from '../../../../core/models/lienzo.model';
import { ModoCanvas } from '../canvas-board/canvas-board';

interface HerramientaRelacion {
  tipo: TipoRelacion;
  etiqueta: string;
}

const RELACIONES: HerramientaRelacion[] = [
  { tipo: 'ASOCIACION', etiqueta: 'Asociación' },
  { tipo: 'AGREGACION', etiqueta: 'Agregación' },
  { tipo: 'COMPOSICION', etiqueta: 'Composición' },
  { tipo: 'HERENCIA', etiqueta: 'Herencia' },
  { tipo: 'REALIZACION', etiqueta: 'Realización' },
  { tipo: 'TEMPLATE_BINDING', etiqueta: 'Template binding' },
];

@Component({
  selector: 'app-toolbox',
  imports: [],
  templateUrl: './toolbox.html',
  styleUrl: './toolbox.scss',
})
export class Toolbox {
  readonly modo = input<ModoCanvas>('seleccionar');
  readonly puedeEditar = input(false);

  readonly cambiarModo = output<ModoCanvas>();
  readonly alinear = output<void>();

  readonly relaciones = RELACIONES;

  alternar(modo: ModoCanvas): void {
    this.cambiarModo.emit(this.modo() === modo ? 'seleccionar' : modo);
  }
}
