"""limitar base_datos_destino a solo postgresql

Revision ID: 1bedc6dc748c
Revises: ea1fb0d3dea4
Create Date: 2026-09-21 10:51:31.623921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bedc6dc748c'
down_revision: Union[str, None] = 'ea1fb0d3dea4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # postgres no deja quitar valores de un enum con ALTER TYPE, hay que
    # reconstruir el tipo
    op.execute("ALTER TABLE configuraciones_transpilacion ALTER COLUMN base_datos TYPE VARCHAR USING base_datos::text")
    op.execute("DROP TYPE base_datos_destino")
    op.execute("CREATE TYPE base_datos_destino AS ENUM ('POSTGRESQL')")
    op.execute("ALTER TABLE configuraciones_transpilacion ALTER COLUMN base_datos TYPE base_datos_destino USING base_datos::base_datos_destino")


def downgrade() -> None:
    op.execute("ALTER TABLE configuraciones_transpilacion ALTER COLUMN base_datos TYPE VARCHAR USING base_datos::text")
    op.execute("DROP TYPE base_datos_destino")
    op.execute("CREATE TYPE base_datos_destino AS ENUM ('POSTGRESQL', 'MYSQL', 'H2')")
    op.execute("ALTER TABLE configuraciones_transpilacion ALTER COLUMN base_datos TYPE base_datos_destino USING base_datos::base_datos_destino")
