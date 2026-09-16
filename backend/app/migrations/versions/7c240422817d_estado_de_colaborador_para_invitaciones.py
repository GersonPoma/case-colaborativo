"""estado de colaborador para invitaciones

Revision ID: 7c240422817d
Revises: cd5cb06eb146
Create Date: 2026-09-16 17:51:14.748854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c240422817d'
down_revision: Union[str, None] = 'cd5cb06eb146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # los colaboradores existentes ya tenían acceso directo antes de este cambio,
    # así que se los da de alta como ACEPTADO para no romper su acceso
    estado_colaborador = sa.Enum(
        'PENDIENTE', 'ACEPTADO', 'RECHAZADO', name='estado_colaborador'
    )
    estado_colaborador.create(op.get_bind())
    op.add_column(
        'colaboradores',
        sa.Column(
            'estado', estado_colaborador, nullable=False, server_default='ACEPTADO'
        ),
    )
    op.alter_column('colaboradores', 'estado', server_default=None)


def downgrade() -> None:
    op.drop_column('colaboradores', 'estado')
    sa.Enum(name='estado_colaborador').drop(op.get_bind())
