"""
Contains classes for different types of Apple Wallet pass information structures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apple_wallet_pass.enums import Alignment, TransitType
from apple_wallet_pass.fields import Field


@dataclass
class PassInformation:
    """Base class for all pass information types."""

    header_fields: List[Field] = field(default_factory=list)
    primary_fields: List[Field] = field(default_factory=list)
    secondary_fields: List[Field] = field(default_factory=list)
    back_fields: List[Field] = field(default_factory=list)
    auxiliary_fields: List[Field] = field(default_factory=list)

    def add_header_field(
        self,
        key: str,
        value: str,
        label: Optional[str] = None,
        text_alignment: Alignment = Alignment.NATURAL,
    ) -> None:
        """Add a field to the header section of the pass.

        Args:
            key: Unique identifier for the field
            value: Value to be displayed
            label: Optional label for the field
            text_alignment: Optional text alignment (defaults to LEFT)
        """
        self.header_fields.append(Field(key, value, label, text_alignment))

    def add_primary_field(
        self,
        key: str,
        value: str,
        label: Optional[str] = None,
        text_alignment: Alignment = Alignment.NATURAL,
    ) -> None:
        """Add a field to the primary section of the pass.

        Args:
            key: Unique identifier for the field
            value: Value to be displayed
            label: Optional label for the field
            text_alignment: Optional text alignment (defaults to LEFT)
        """
        self.primary_fields.append(Field(key, value, label, text_alignment))

    def add_secondary_field(
        self,
        key: str,
        value: str,
        label: Optional[str] = None,
        text_alignment: Alignment = Alignment.NATURAL,
    ) -> None:
        """Add a field to the secondary section of the pass.

        Args:
            key: Unique identifier for the field
            value: Value to be displayed
            label: Optional label for the field
            text_alignment: Optional text alignment (defaults to LEFT)
        """
        self.secondary_fields.append(Field(key, value, label, text_alignment))

    def add_back_field(
        self,
        key: str,
        value: str,
        label: Optional[str] = None,
        text_alignment: Alignment = Alignment.NATURAL,
    ) -> None:
        """Add a field to the back section of the pass.

        Args:
            key: Unique identifier for the field
            value: Value to be displayed
            label: Optional label for the field
            text_alignment: Optional text alignment (defaults to LEFT)
        """
        self.back_fields.append(Field(key, value, label, text_alignment))

    def add_auxiliary_field(
        self,
        key: str,
        value: str,
        label: Optional[str] = None,
        text_alignment: Alignment = Alignment.NATURAL,
    ) -> None:
        """Add a field to the auxiliary section of the pass.

        Args:
            key: Unique identifier for the field
            value: Value to be displayed
            label: Optional label for the field
            text_alignment: Optional text alignment (defaults to LEFT)
        """
        self.auxiliary_fields.append(Field(key, value, label, text_alignment))

    def json_dict(self) -> Dict[str, Any]:
        """Convert the pass information to a dictionary format for JSON serialization."""
        result = {}
        field_mapping = {
            "headerFields": self.header_fields,
            "primaryFields": self.primary_fields,
            "secondaryFields": self.secondary_fields,
            "backFields": self.back_fields,
            "auxiliaryFields": self.auxiliary_fields,
        }

        for key, fields in field_mapping.items():
            if fields:
                result[key] = [f.json_dict() for f in fields]

        return result


@dataclass
class BoardingPass(PassInformation):
    """Represents a boarding pass type of Apple Wallet pass."""

    transit_type: TransitType = TransitType.AIR
    jsonname: str = field(default="boardingPass", init=False)

    def json_dict(self) -> Dict[str, Any]:
        """Convert the boarding pass to a dictionary format for JSON serialization."""
        result = super().json_dict()
        result["transitType"] = self.transit_type
        return result


@dataclass
class Coupon(PassInformation):
    """Represents a coupon type of Apple Wallet pass."""

    jsonname: str = field(default="coupon", init=False)


@dataclass
class EventTicket(PassInformation):
    """Represents an event ticket type of Apple Wallet pass."""

    jsonname: str = field(default="eventTicket", init=False)


@dataclass
class Generic(PassInformation):
    """Represents a generic type of Apple Wallet pass."""

    jsonname: str = field(default="generic", init=False)


@dataclass
class StoreCard(PassInformation):
    """Represents a store card type of Apple Wallet pass."""

    jsonname: str = field(default="storeCard", init=False)
