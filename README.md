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