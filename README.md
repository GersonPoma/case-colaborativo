Estructura del prouecto

case-colaborativo/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── frontend-angular/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── src/
│
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── alembic.ini
    ├── .env
    └── app/
        ├── main.py
        ├── config/
        ├── models/
        ├── schemas/
        ├── routers/
        ├── services/
        ├── templates/
        ├── websocket/
        └── migrations/


estructura del backend

backend/
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env
├── .env.example
│
└── app/
    ├── __init__.py
    ├── main.py
    │
    ├── config/
    │   ├── __init__.py
    │   ├── database.py
    │   └── settings.py
    │
    ├── core/
    │   ├── __init__.py
    │   ├── security.py
    │   ├── dependencies.py
    │   └── exceptions.py
    │
    ├── modules/
    │   ├── __init__.py
    │   ├── auth/                           ← Paquete 1: Gestión de Accesos y Usuarios
    │   │   ├── __init__.py
    │   │   ├── model.py                    ← tabla users
    │   │   ├── schema.py
    │   │   ├── repository.py
    │   │   ├── service.py                  ← register, login, recover_password
    │   │   └── router.py
    │   │
    │   ├── workspace/                      ← Paquete 2: Gestión del Espacio de Trabajo
    │   │   ├── __init__.py
    │   │   ├── model.py                    ← tablas projects, collaborators, versions
    │   │   ├── schema.py
    │   │   ├── repository.py
    │   │   ├── service.py                  ← create_project, invite, change_role, restore_version
    │   │   └── router.py
    │   │
    │   ├── canvas/                         ← Paquete 3: Edición y Diseño del Lienzo
    │   │   ├── __init__.py
    │   │   ├── model.py                     ← tabla diagrams (JSONB)
    │   │   ├── schema.py
    │   │   ├── repository.py
    │   │   ├── service.py                  ← edit, undo_redo, copy_paste, align
    │   │   └── router.py
    │   │
    │   └── interoperability/               ← Paquete 4: Interoperabilidad y Generación
    │       ├── __init__.py
    │       ├── schema.py                   ← no tiene tabla propia, usa canvas/model.py
    │       ├── service.py                  ← import_xmi, export_xmi, export_image, generate_springboot
    │       └── router.py
    │
    ├── websocket/             ← colaboración en tiempo real
    │   ├── __init__.py
    │   ├── manager.py
    │   └── router.py
    │
    ├── templates/             ← plantillas Jinja2 para generar código Java
    │   ├── Entity.java.j2
    │   ├── Repository.java.j2
    │   ├── Service.java.j2
    │   └── Controller.java.j2
    │
    └── migrations/            ← migraciones Alembic
        └── versions/


routers/      ← recibe HTTP, devuelve respuesta        (S)
services/     ← lógica de negocio                      (S)
repositories/ ← consultas a la BD, nada más            (S)
models/       ← estructura de datos                    (S)
schemas/      ← validación entrada/salida              (S)


modules/
├── auth/
│   └── model.py        ← User, Profile
│
├── workspace/
│   └── model.py        ← Project, Collaborator, HistorialVersiones, Mensaje_Chat
│
├── canvas/
│   └── model.py        ← (vacío, usa Project de workspace)
│
└── interoperability/
    └── model.py        ← Configuracion_Transpilacion


frontend-angular/
├── Dockerfile
├── docker-compose.yml
├── angular.json
├── package.json
├── tsconfig.json
├── .env
│
└── src/
    ├── main.ts
    ├── index.html
    │
    ├── app/
    │   ├── app.component.ts
    │   ├── app.config.ts
    │   ├── app.routes.ts
    │   │
    │   ├── core/                          ← servicios globales, guards, interceptors
    │   │   ├── guards/
    │   │   │   └── auth.guard.ts          ← protege rutas privadas
    │   │   ├── interceptors/
    │   │   │   └── auth.interceptor.ts    ← agrega JWT a cada request
    │   │   ├── services/
    │   │   │   ├── auth.service.ts        ← login, register, token
    │   │   │   └── websocket.service.ts   ← conexión WebSocket global
    │   │   └── models/
    │   │       ├── user.model.ts          ← interfaces TypeScript
    │   │       ├── project.model.ts
    │   │       └── diagram.model.ts
    │   │
    │   ├── shared/                        ← componentes reutilizables
    │   │   ├── components/
    │   │   │   ├── navbar/
    │   │   │   ├── sidebar/
    │   │   │   ├── modal/
    │   │   │   └── loader/
    │   │   └── pipes/
    │   │       └── date-format.pipe.ts
    │   │
    │   └── modules/                       ← un módulo por paquete PUDS
    │       │
    │       ├── auth/                      ← Paquete 1
    │       │   ├── pages/
    │       │   │   ├── login/
    │       │   │   │   ├── login.component.ts
    │       │   │   │   ├── login.component.html
    │       │   │   │   └── login.component.scss
    │       │   │   ├── register/
    │       │   │   │   ├── register.component.ts
    │       │   │   │   ├── register.component.html
    │       │   │   │   └── register.component.scss
    │       │   │   └── recover-password/
    │       │   │       ├── recover-password.component.ts
    │       │   │       ├── recover-password.component.html
    │       │   │       └── recover-password.component.scss
    │       │   └── auth.routes.ts
    │       │
    │       ├── workspace/                 ← Paquete 2
    │       │   ├── pages/
    │       │   │   ├── project-list/
    │       │   │   │   ├── project-list.component.ts
    │       │   │   │   ├── project-list.component.html
    │       │   │   │   └── project-list.component.scss
    │       │   │   ├── project-detail/
    │       │   │   │   ├── project-detail.component.ts
    │       │   │   │   ├── project-detail.component.html
    │       │   │   │   └── project-detail.component.scss
    │       │   │   └── collaborators/
    │       │   │       ├── collaborators.component.ts
    │       │   │       ├── collaborators.component.html
    │       │   │       └── collaborators.component.scss
    │       │   ├── services/
    │       │   │   └── workspace.service.ts  ← llama al backend
    │       │   └── workspace.routes.ts
    │       │
    │       ├── canvas/                    ← Paquete 3 — el más importante
    │       │   ├── pages/
    │       │   │   └── editor/
    │       │   │       ├── editor.component.ts
    │       │   │       ├── editor.component.html
    │       │   │       └── editor.component.scss
    │       │   ├── components/
    │       │   │   ├── toolbar/           ← herramientas del lienzo
    │       │   │   │   ├── toolbar.component.ts
    │       │   │   │   ├── toolbar.component.html
    │       │   │   │   └── toolbar.component.scss
    │       │   │   ├── chat-panel/        ← CU-23 chat del proyecto
    │       │   │   │   ├── chat-panel.component.ts
    │       │   │   │   ├── chat-panel.component.html
    │       │   │   │   └── chat-panel.component.scss
    │       │   │   ├── collaborators-cursors/  ← cursores en tiempo real
    │       │   │   │   ├── collaborators-cursors.component.ts
    │       │   │   │   └── collaborators-cursors.component.html
    │       │   │   └── ia-panel/          ← chat con IA
    │       │   │       ├── ia-panel.component.ts
    │       │   │       ├── ia-panel.component.html
    │       │   │       └── ia-panel.component.scss
    │       │   ├── services/
    │       │   │   ├── canvas.service.ts      ← AntV X6, nodos, relaciones
    │       │   │   ├── yjs.service.ts         ← CRDTs, sincronización
    │       │   │   └── ia.service.ts          ← llama al backend IA
    │       │   └── canvas.routes.ts
    │       │
    │       └── interoperability/          ← Paquete 4
    │           ├── components/
    │           │   └── codegen-config/    ← CU-27 configurar transpilación
    │           │       ├── codegen-config.component.ts
    │           │       ├── codegen-config.component.html
    │           │       └── codegen-config.component.scss
    │           ├── services/
    │           │   └── interoperability.service.ts  ← import/export XMI, generar código
    │           └── interoperability.routes.ts
    │
    └── environments/
        ├── environment.ts           ← local
        └── environment.production.ts ← producción


Entonces la estructura correcta sería
core/
└── services/
    └── auth.service.ts        ← estado global: token, usuario actual, isLoggedIn

modules/
└── auth/
    ├── services/
    │   └── auth-api.service.ts ← llamadas HTTP al backend
    └── pages/
        ├── login/
        ├── register/
        └── recover-password/