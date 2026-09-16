import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideCode, LucideFileCode, LucideSparkles, LucideUsers } from '@lucide/angular';

@Component({
  selector: 'app-home',
  imports: [RouterLink, LucideUsers, LucideSparkles, LucideFileCode, LucideCode],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {}
