"""Channel model for chatom.

This module provides the base Channel class representing a chat channel or room.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from .base import Field, Identifiable

if TYPE_CHECKING:
    pass

__all__ = ("Channel", "ChannelType")


class ChannelType(str, Enum):
    """Types of chat channels."""

    PUBLIC = "public"
    """A public channel visible to all members."""

    PRIVATE = "private"
    """A private channel with restricted access."""

    DIRECT = "direct"
    """A direct message between two users."""

    GROUP = "group"
    """A group direct message between multiple users."""

    THREAD = "thread"
    """A thread within another channel."""

    FORUM = "forum"
    """A forum channel for organized discussions."""

    ANNOUNCEMENT = "announcement"
    """An announcement or broadcast channel."""

    UNKNOWN = "unknown"
    """Unknown channel type."""


class Channel(Identifiable):
    """Represents a channel or room on a chat platform.

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the channel.
        topic: Channel topic or description.
        channel_type: Type of the channel (public, private, etc.).
        is_archived: Whether the channel is archived.
        member_count: Number of members in the channel.
        parent: Parent channel (for threads/subchannels).
        parent_id: ID of the parent channel (derived from parent).
    """

    topic: str = Field(
        default="",
        description="Channel topic or description.",
    )
    channel_type: ChannelType = Field(
        default=ChannelType.UNKNOWN,
        description="Type of the channel.",
    )
    is_archived: bool = Field(
        default=False,
        description="Whether the channel is archived.",
    )
    member_count: Optional[int] = Field(
        default=None,
        description="Number of members in the channel.",
    )
    parent: Optional["Channel"] = Field(
        default=None,
        description="Parent channel (for threads/subchannels).",
    )

    @property
    def parent_id(self) -> str:
        """Get the parent channel's ID.

        Returns:
            str: The parent channel ID or empty string if no parent.
        """
        return self.parent.id if self.parent else ""

    @property
    def is_thread(self) -> bool:
        """Check if this channel is a thread.

        Returns:
            bool: True if this is a thread channel.
        """
        return self.channel_type == ChannelType.THREAD

    @property
    def is_direct_message(self) -> bool:
        """Check if this channel is a direct message.

        Returns:
            bool: True if this is a DM or group DM.
        """
        return self.channel_type in (ChannelType.DIRECT, ChannelType.GROUP)

    @property
    def is_dm(self) -> bool:
        """Alias for is_direct_message.

        Returns:
            bool: True if this is a DM or group DM.
        """
        return self.is_direct_message

    @property
    def is_public(self) -> bool:
        """Check if this channel is public.

        Returns:
            bool: True if this is a public channel.
        """
        return self.channel_type == ChannelType.PUBLIC

    @property
    def is_private(self) -> bool:
        """Check if this channel is private.

        Returns:
            bool: True if this is a private channel.
        """
        return self.channel_type == ChannelType.PRIVATE

    @property
    def is_resolvable(self) -> bool:
        """Check if this channel can be resolved by a backend.

        A channel is resolvable if it has an id or name.

        Returns:
            bool: True if the channel can potentially be resolved.
        """
        return bool(self.id or self.name)
