from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config.database import Base
from app.config.settings import settings

# Importa aquí los modelos de cada módulo para que Alembic los detecte en el autogenerate
from app.modules.auth.model import Perfil, Usuario  # noqa: F401
from app.modules.workspace.model import (  # noqa: F401
    Colaborador,
    HistorialVersiones,
    MensajeChat,
    Proyecto,
)

config = context.config

DB_URL = (
    f"postgresql+psycopg2://{settings.DB_USERNAME}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
config.set_main_option("sqlalchemy.url", DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
