"""Unit tests for field classes: camelCase mapping and validation."""

# Standard Library
from datetime import datetime
from uuid import UUID

# Third Party Stuff
import pytest

from apple_wallet_pass.enums import Alignment, BarcodeFormat, DateStyle
from apple_wallet_pass.fields import (
    Barcode,
    CurrencyField,
    DateField,
    Field,
    IBeacon,
    Location,
    NumberField,
)


def test_field_json_dict_uses_passkit_keys():
    field = Field("my_key", "value", "Label", Alignment.LEFT)
    field.change_message = "Updated to %@"
    assert field.json_dict() == {
        "key": "my_key",
        "value": "value",
        "label": "Label",
        "changeMessage": "Updated to %@",
        "textAlignment": "PKTextAlignmentLeft",
    }


def test_field_requires_a_key():
    with pytest.raises(ValueError):
        Field("", "value")


def test_date_field_styles_and_validation():
    field = DateField(
        "date",
        datetime(2026, 12, 1, 20, 0),
        "Date",
        date_style=DateStyle.MEDIUM,
        time_style=DateStyle.SHORT,
        ignores_time_zone=True,
    )
    data = field.json_dict()
    assert data["dateStyle"] == "PKDateStyleMedium"
    assert data["timeStyle"] == "PKDateStyleShort"
    assert data["ignoresTimeZone"] is True
    with pytest.raises(ValueError):
        DateField("bad", "not a datetime")


def test_number_field_rejects_non_numbers():
    assert NumberField("n", 42).json_dict()["numberStyle"] == (
        "PKNumberStyleDecimal"
    )
    with pytest.raises(ValueError):
        NumberField("n", "42")


def test_currency_field_validates_iso_code():
    field = CurrencyField("price", 9.99, "Price", currency_code="usd")
    assert field.json_dict()["currencyCode"] == "USD"
    with pytest.raises(ValueError):
        CurrencyField("price", 9.99, currency_code="TOOLONG")
    with pytest.raises(ValueError):
        CurrencyField("price", 9.99, currency_code="US1")


def test_barcode_json_dict_and_empty_message():
    barcode = Barcode("hello", BarcodeFormat.QR, alt_text="hi")
    assert barcode.json_dict() == {
        "format": "PKBarcodeFormatQR",
        "message": "hello",
        "messageEncoding": "iso-8859-1",
        "altText": "hi",
    }
    with pytest.raises(ValueError):
        Barcode("", BarcodeFormat.QR)


def test_location_bounds():
    location = Location(48.8566, 2.3522)
    assert location.json_dict() == {
        "latitude": 48.8566,
        "longitude": 2.3522,
        "altitude": 0.0,
    }
    with pytest.raises(ValueError):
        Location(91, 0)
    with pytest.raises(ValueError):
        Location(0, 181)


def test_ibeacon_validates_major_minor_and_uuid():
    beacon = IBeacon("74278bda-b644-4520-8f0c-720eaf059935", 1, 2)
    assert beacon.json_dict()["proximityUUID"] == (
        "74278bda-b644-4520-8f0c-720eaf059935"
    )
    with pytest.raises(ValueError):
        IBeacon(UUID(int=0), 65536, 0)
    with pytest.raises(ValueError):
        IBeacon("not-a-uuid", 0, 0)
