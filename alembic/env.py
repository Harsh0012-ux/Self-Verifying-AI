from dotenv import load_dotenv
load_dotenv()

from alembic import context
from app.config import settings
from app.models import Base
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
def run_migrations_online():
    from sqlalchemy import engine_from_config, pool
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()
run_migrations_online()
