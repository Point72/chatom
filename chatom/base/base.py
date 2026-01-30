"""Base model classes for chatom.

This module provides the foundational model classes that all chatom
data structures inherit from. It uses Pydantic for data validation
and serialization.
"""

from typing import Any, Dict, TypeVar

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field

__all__ = ("BaseModel", "Field", "Identifiable")

T = TypeVar("T", bound="BaseModel")


class BaseModel(PydanticBaseModel):
    """Base model class for all chatom data structures.

    Provides common configuration and utilities for all models.
    Inherits from Pydantic's BaseModel for validation and serialization.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="allow",
        populate_by_name=True,
        validate_assignment=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation.

        Returns:
            Dict[str, Any]: Dictionary representation of the model.
        """
        return self.model_dump(exclude_none=True)

    def copy_with(self: T, **kwargs: Any) -> T:
        """Create a copy of the model with updated fields.

        Args:
            **kwargs: Fields to update in the copy.

        Returns:
            A new instance with the updated fields.
        """
        return self.model_copy(update=kwargs)


class Identifiable(BaseModel):
    """Base class for models with an identifier.

    Provides common id and name fields that most chat entities have.

    Objects can be created with partial information (e.g., just a name)
    and later resolved by a backend to populate missing fields like id.
    Use the `is_complete` property to check if an object has all required
    fields populated.
    """

    id: str = Field(
        default="",
        description="Platform-specific unique identifier.",
    )
    name: str = Field(
        default="",
        description="Human-readable name or display name.",
    )

    @property
    def is_complete(self) -> bool:
        """Check if this object has all required fields populated.

        An object is considered complete if it has an id. Subclasses may
        override this to add additional requirements.

        Returns:
            bool: True if the object is complete.
        """
        return bool(self.id)

    @property
    def is_resolvable(self) -> bool:
        """Check if this object has enough info to be resolved by a backend.

        An object is resolvable if it has at least an id OR a name that
        can be used to look it up.

        Returns:
            bool: True if the object can potentially be resolved.
        """
        return bool(self.id or self.name)
