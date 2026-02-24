"""
Alembic environment — configuración de migraciones.
Usa DATABASE_SYNC_URL (psycopg2) para conexión síncrona.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Añadir apps/api al path para importar modelos y config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.config import settings  # noqa: E402
from models.base import Base  # noqa: E402

# Importar todos los modelos para que Alembic los detecte en autogenerate
import models  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos para autogenerate
target_metadata = Base.metadata

# Sobreescribir la URL desde la variable de entorno (conexión síncrona con psycopg2)
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)


def run_migrations_offline() -> None:
    """Genera SQL sin conectarse a la BD (útil para revisión o CI)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones con conexión activa a la BD."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
