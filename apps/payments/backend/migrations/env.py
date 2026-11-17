"""Alembic runtime: connects to the database (online) or prints SQL without connecting (offline / --sql)."""

from logging.config import fileConfig

from alembic import context

from northstar_payments.common.db import get_engine
from northstar_payments.common.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL that WOULD run. Like `terraform plan`, nothing changes."""
    context.configure(
        url="mssql+pyodbc://",  # dialect only; no connection is made
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """`alembic upgrade head`: connect and apply every migration not yet recorded in `alembic_version`."""
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
