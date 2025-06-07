from pydantic import BaseModel, Field

__all__ = ("User",)


class User(BaseModel):
    user: str = Field(
        description="The username of the author of the message.",
    )
    email: str = Field(
        default="",
        description="email of the author, for mentions",
    )
    id: str = Field(
        default="",
        description="uid of the author, for mentions",
    )
