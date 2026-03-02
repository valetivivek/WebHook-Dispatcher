from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic can discover them
from app.models.webhook import Webhook  # noqa: E402, F401
from app.models.event import Event  # noqa: E402, F401
from app.models.delivery_attempt import DeliveryAttempt  # noqa: E402, F401
