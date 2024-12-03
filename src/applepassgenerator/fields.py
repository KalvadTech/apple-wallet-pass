from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID

from applepassgenerator.enums import (
    Alignment,
    BarcodeFormat,
    DateStyle,
    NumberStyle,
)


class Field:
    """Base class for all pass fields."""

    def __init__(self, key: str, value: Any, label: str = "") -> None:
        """
        Initialize a basic field.

        Args:
            key: Unique identifier for the field within its scope
            value: Value of the field
            label: Optional label text for the field

        Raises:
            ValueError: If key is empty or None
        """
        if not key:
            raise ValueError("Field key cannot be empty")

        self._key = key
        self._value = value
        self._label = label
        self._change_message = ""
        self._text_alignment = Alignment.LEFT

    @property
    def key(self) -> str:
        return self._key

    @property
    def value(self) -> Any:
        return self._value

    @property
    def label(self) -> str:
        return self._label

    @property
    def change_message(self) -> str:
        return self._change_message

    @change_message.setter
    def change_message(self, value: str) -> None:
        self._change_message = value

    @property
    def text_alignment(self) -> Alignment:
        return self._text_alignment

    @text_alignment.setter
    def text_alignment(self, value: Alignment) -> None:
        self._text_alignment = value

    def json_dict(self) -> Dict[str, Any]:
        """Convert the field to a dictionary for JSON serialization."""
        return {
            "key": self._key,
            "value": self._value,
            "label": self._label,
            "changeMessage": self._change_message,
            "textAlignment": self._text_alignment.value,
        }


class DateField(Field):
    """Field for displaying dates and times."""

    def __init__(
        self,
        key: str,
        value: datetime,
        label: str = "",
        date_style: DateStyle = DateStyle.SHORT,
        time_style: DateStyle = DateStyle.SHORT,
        ignores_time_zone: bool = False,
    ) -> None:
        """
        Initialize a date field.

        Args:
            key: Unique identifier for the field
            value: DateTime value to display
            label: Optional label text
            date_style: Style of date to display
            time_style: Style of time to display
            ignores_time_zone: Whether to ignore timezone information
        """
        if not isinstance(value, datetime):
            raise ValueError("Value must be a datetime object")

        super().__init__(key, value, label)
        self._date_style = date_style
        self._time_style = time_style
        self._is_relative = False
        self._ignores_time_zone = ignores_time_zone

    def json_dict(self) -> Dict[str, Any]:
        data = super().json_dict()
        data.update(
            {
                "dateStyle": self._date_style.value,
                "timeStyle": self._time_style.value,
                "isRelative": self._is_relative,
            }
        )
        if self._ignores_time_zone:
            data["ignoresTimeZone"] = self._ignores_time_zone
        return data


class NumberField(Field):
    """Field for displaying numbers."""

    def __init__(self, key: str, value: float, label: str = "") -> None:
        """
        Initialize a number field.

        Args:
            key: Unique identifier for the field
            value: Numeric value to display
            label: Optional label text
        """
        if not isinstance(value, (int, float)):
            raise ValueError("Value must be a number")

        super().__init__(key, value, label)
        self._number_style = NumberStyle.DECIMAL

    def json_dict(self) -> Dict[str, Any]:
        data = super().json_dict()
        data["numberStyle"] = self._number_style.value
        return data


class CurrencyField(NumberField):
    """Field for displaying currency values."""

    def __init__(
        self, key: str, value: float, label: str = "", currency_code: str = ""
    ) -> None:
        """
        Initialize a currency field.

        Args:
            key: Unique identifier for the field
            value: Monetary value to display
            label: Optional label text
            currency_code: ISO 4217 currency code (e.g., 'USD', 'EUR')

        Raises:
            ValueError: If currency_code is not a valid 3-letter code
        """
        super().__init__(key, value, label)
        if currency_code and (len(currency_code) != 3 or not currency_code.isalpha()):
            raise ValueError("Currency code must be a 3-letter ISO 4217 code")
        self._currency_code = currency_code.upper()

    def json_dict(self) -> Dict[str, Any]:
        data = super().json_dict()
        if self._currency_code:
            data["currencyCode"] = self._currency_code
        return data


class Barcode:
    """Represents a barcode that can be displayed on the pass."""

    def __init__(
        self,
        message: str,
        format: BarcodeFormat = BarcodeFormat.PDF417,
        alt_text: str = "",
        message_encoding: str = "iso-8859-1",
    ) -> None:
        """
        Initialize a barcode.

        Args:
            message: Message or payload to be displayed as a barcode
            format: Format of the barcode
            alt_text: Optional text displayed near the barcode
            message_encoding: Text encoding used to convert the message

        Raises:
            ValueError: If message is empty or None
        """
        if not message:
            raise ValueError("Barcode message cannot be empty")

        self._format = format
        self._message = message
        self._message_encoding = message_encoding
        self._alt_text = alt_text

    def json_dict(self) -> Dict[str, Any]:
        """Convert the barcode to a dictionary for JSON serialization."""
        data = {
            "format": self._format.value,
            "message": self._message,
            "messageEncoding": self._message_encoding,
        }
        if self._alt_text:
            data["altText"] = self._alt_text
        return data


class Location:
    """Represents a geographic location relevant to the pass."""

    def __init__(
        self,
        latitude: Union[float, str],
        longitude: Union[float, str],
        altitude: Union[float, str] = 0.0,
    ) -> None:
        """
        Initialize a location.

        Args:
            latitude: Latitude in degrees (-90 to 90)
            longitude: Longitude in degrees (-180 to 180)
            altitude: Optional altitude in meters

        Raises:
            ValueError: If latitude or longitude are invalid
        """
        try:
            self._latitude = float(latitude)
            if not -90 <= self._latitude <= 90:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Latitude must be a number between -90 and 90")

        try:
            self._longitude = float(longitude)
            if not -180 <= self._longitude <= 180:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Longitude must be a number between -180 and 180")

        try:
            self._altitude = float(altitude)
        except (ValueError, TypeError):
            self._altitude = 0.0

        self._distance: Optional[float] = None
        self._relevant_text: str = ""

    @property
    def relevant_text(self) -> str:
        return self._relevant_text

    @relevant_text.setter
    def relevant_text(self, value: str) -> None:
        self._relevant_text = value

    @property
    def distance(self) -> Optional[float]:
        return self._distance

    @distance.setter
    def distance(self, value: Optional[float]) -> None:
        if value is not None:
            try:
                self._distance = float(value)
            except (ValueError, TypeError):
                raise ValueError("Distance must be a number")
        else:
            self._distance = None

    def json_dict(self) -> Dict[str, Any]:
        """Convert the location to a dictionary for JSON serialization."""
        data = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "altitude": self._altitude,
        }
        if self._distance is not None:
            data["distance"] = self._distance
        if self._relevant_text:
            data["relevantText"] = self._relevant_text
        return data


class IBeacon:
    """Represents an iBeacon for proximity detection."""

    def __init__(
        self, proximity_uuid: Union[str, UUID], major: int, minor: int
    ) -> None:
        """
        Initialize an iBeacon.

        Args:
            proximity_uuid: UUID for the beacon
            major: Major identifier (0-65535)
            minor: Minor identifier (0-65535)

        Raises:
            ValueError: If major/minor are out of range or UUID is invalid
        """
        # Validate and convert UUID
        try:
            if isinstance(proximity_uuid, str):
                proximity_uuid = UUID(proximity_uuid)
            self._proximity_uuid = str(proximity_uuid)
        except (ValueError, AttributeError, TypeError):
            raise ValueError("Invalid UUID format")

        # Validate major and minor values
        try:
            self._major = int(major)
            self._minor = int(minor)
            if not (0 <= self._major <= 65535 and 0 <= self._minor <= 65535):
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Major and minor must be integers between 0 and 65535")

        self._relevant_text: str = ""

    @property
    def relevant_text(self) -> str:
        return self._relevant_text

    @relevant_text.setter
    def relevant_text(self, value: str) -> None:
        self._relevant_text = value

    def json_dict(self) -> Dict[str, Any]:
        """Convert the iBeacon to a dictionary for JSON serialization."""
        data = {
            "proximityUUID": self._proximity_uuid,
            "major": self._major,
            "minor": self._minor,
        }
        if self._relevant_text:
            data["relevantText"] = self._relevant_text
        return data
