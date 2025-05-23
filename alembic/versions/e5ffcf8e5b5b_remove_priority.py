"""remove_priority

Revision ID: e5ffcf8e5b5b
Revises: 06a468fbb1be
Create Date: 2025-04-25 08:40:36.481182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5ffcf8e5b5b'
down_revision: Union[str, None] = '06a468fbb1be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('operations', 'priority')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('operations', sa.Column('priority', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
