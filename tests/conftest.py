"""
Shared fixtures for the test suite.

The certificates in tests/fixtures are throwaway self-signed test credentials
generated for this project only (a fake "Test WWDR CA" issuing a fake pass
certificate, valid 2020-2050). They are NOT real Apple-issued credentials and
are safe to commit.
"""

# Standard Library
import base64
import zipfile
from pathlib import Path

# Third Party Stuff
import pytest

from apple_wallet_pass.apple_pass import ApplePass
from apple_wallet_pass.enums import BarcodeFormat
from apple_wallet_pass.fields import Barcode
from apple_wallet_pass.pass_information import Generic

FIXTURES = Path(__file__).parent / "fixtures"

CERTIFICATE = FIXTURES / "certificate.pem"
KEY = FIXTURES / "key.pem"
KEY_PASSWORD = "test-pass"
KEY_NOPASS = FIXTURES / "key-nopass.pem"
WWDR_CERTIFICATE = FIXTURES / "wwdr.pem"

GOLDEN_PASS_JSON = FIXTURES / "golden-pass.json"
GOLDEN_MANIFEST_JSON = FIXTURES / "golden-manifest.json"
GOLDEN_SIGNATURE_DER = FIXTURES / "golden-signature.der"

# 1x1 transparent PNG
ICON_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture(scope="session")
def apple_pass() -> ApplePass:
    """The canonical pass used by the golden comparisons.

    Must stay in sync with the content used to record the golden files
    (originally generated with cryptography 38.0.4).
    """
    info = Generic()
    info.add_primary_field("event", "Test Event", "EVENT")
    info.add_secondary_field("date", "2026-12-01", "DATE")
    pass_ = ApplePass(
        pass_information=info,
        pass_type_identifier="pass.com.kalvad.test",
        organization_name="Kalvad Test",
        team_identifier="TEAM123456",
        serial_number="0001",
        description="Test pass",
        barcode=Barcode(
            message="1234567890", format=BarcodeFormat.PDF417, alt_text="1234"
        ),
    )
    pass_.add_file("icon.png", ICON_PNG)
    return pass_


@pytest.fixture()
def pkpass_path(apple_pass: ApplePass, tmp_path: Path) -> Path:
    """Create a real .pkpass on disk and return its path."""
    out = tmp_path / "test.pkpass"
    apple_pass.create(
        CERTIFICATE, KEY, WWDR_CERTIFICATE, out, password=KEY_PASSWORD
    )
    return out


@pytest.fixture()
def pkpass_members(pkpass_path: Path) -> dict:
    """Return the .pkpass zip members as a name -> bytes mapping."""
    with zipfile.ZipFile(pkpass_path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}
