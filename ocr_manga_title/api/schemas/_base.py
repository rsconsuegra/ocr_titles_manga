from pydantic import BaseModel, ConfigDict


class ORMSchema(BaseModel):
    """Base for response schemas that map from SQLAlchemy ORM models."""

    model_config = ConfigDict(from_attributes=True)
