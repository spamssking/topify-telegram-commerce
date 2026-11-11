"""merge migration heads

Revision ID: f66aa857ee16
Revises: 3383760fe499, 5869bbc07af4
Create Date: 2026-09-12 07:47:53.358898

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'f66aa857ee16'
down_revision: Union[str, Sequence[str], None] = ('3383760fe499', '5869bbc07af4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
