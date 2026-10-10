"""
End-to-end tests: generate a real .pkpass and compare it against golden
artifacts recorded with cryptography 38.0.4 (the last version whose PKCS#7
builder allowed Apple's mandated SHA1).

The signature comparison normalizes the two inherently time-dependent parts
(signingTime attribute and the RSA signature value covering it); everything
else must be byte-identical to what the old library produced, which is what
makes the output acceptable to Apple.
"""

# Standard Library
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from io import BytesIO

# Third Party Stuff
import pytest
from asn1crypto import cms
from conftest import (
    CERTIFICATE,
    GOLDEN_MANIFEST_JSON,
    GOLDEN_PASS_JSON,
    GOLDEN_SIGNATURE_DER,
    ICON_PNG,
    KEY,
    KEY_NOPASS,
    KEY_PASSWORD,
    WWDR_CERTIFICATE,
)
from cryptography.hazmat.primitives.serialization import pkcs7

from apple_wallet_pass.apple_pass import ApplePass
from apple_wallet_pass.pass_information import Generic


def _normalize_signature(der: bytes) -> bytes:
    """Zero out time-dependent parts of a PKCS#7 signature for comparison."""
    info = cms.ContentInfo.load(der)
    signer = info["content"]["signer_infos"][0]
    for attr in signer["signed_attrs"]:
        if attr["type"].native == "signing_time":
            attr["values"] = [
                cms.Time({"utc_time": datetime(2026, 1, 1, tzinfo=timezone.utc)})
            ]
    signer["signature"] = b"\x00" * len(signer["signature"].native)
    return info.dump()


def test_creates_pkpass_with_expected_members(pkpass_members):
    assert set(pkpass_members) == {
        "pass.json",
        "manifest.json",
        "signature",
        "icon.png",
    }


def test_pass_json_matches_golden(pkpass_members):
    assert pkpass_members["pass.json"] == GOLDEN_PASS_JSON.read_bytes()
    pass_json = json.loads(pkpass_members["pass.json"])
    assert pass_json["passTypeIdentifier"] == "pass.com.kalvad.test"
    assert pass_json["teamIdentifier"] == "TEAM123456"
    assert pass_json["serialNumber"] == "0001"
    assert pass_json["formatVersion"] == 1
    assert pass_json["generic"]["primaryFields"][0]["value"] == "Test Event"
    assert pass_json["barcode"]["format"] == "PKBarcodeFormatPDF417"


def test_manifest_matches_golden_and_hashes(pkpass_members):
    manifest_bytes = pkpass_members["manifest.json"]
    assert manifest_bytes == GOLDEN_MANIFEST_JSON.read_bytes()
    manifest = json.loads(manifest_bytes)
    for name in ("pass.json", "icon.png"):
        expected = hashlib.sha1(pkpass_members[name]).hexdigest()  # noqa: S324
        assert manifest[name] == expected


def test_icon_roundtrips_byte_for_byte(pkpass_members):
    assert pkpass_members["icon.png"] == ICON_PNG


def test_signature_contains_pass_and_wwdr_certificates(pkpass_members):
    certs = pkcs7.load_der_pkcs7_certificates(pkpass_members["signature"])
    subjects = [c.subject.rfc4514_string() for c in certs]
    assert any("Pass Type ID: pass.com.kalvad.test" in s for s in subjects)
    assert any("Test WWDR CA" in s for s in subjects)


def test_signature_uses_sha1_as_apple_requires(pkpass_members):
    info = cms.ContentInfo.load(pkpass_members["signature"])
    signed_data = info["content"]
    digest_algos = [a["algorithm"].native for a in signed_data["digest_algorithms"]]
    assert digest_algos == ["sha1"]
    signer = signed_data["signer_infos"][0]
    assert signer["digest_algorithm"]["algorithm"].native == "sha1"
    message_digest = None
    for attr in signer["signed_attrs"]:
        if attr["type"].native == "message_digest":
            message_digest = attr["values"][0].native
    assert message_digest == hashlib.sha1(  # noqa: S324
        pkpass_members["manifest.json"]
    ).digest()


def test_signature_structure_matches_golden(pkpass_members):
    golden = GOLDEN_SIGNATURE_DER.read_bytes()
    assert _normalize_signature(pkpass_members["signature"]) == (
        _normalize_signature(golden)
    )


def test_signature_verifies_with_openssl(pkpass_members, tmp_path):
    """Independent validation: the OS OpenSSL must accept the signature."""
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("openssl binary not available")
    (tmp_path / "manifest.json").write_bytes(pkpass_members["manifest.json"])
    (tmp_path / "signature.der").write_bytes(pkpass_members["signature"])
    result = subprocess.run(
        [
            openssl,
            "smime",
            "-verify",
            "-inform",
            "DER",
            "-in",
            str(tmp_path / "signature.der"),
            "-content",
            str(tmp_path / "manifest.json"),
            "-CAfile",
            str(WWDR_CERTIFICATE),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Verification successful" in (result.stdout + result.stderr)


def test_create_with_unencrypted_key(apple_pass, tmp_path):
    out = tmp_path / "nopass.pkpass"
    apple_pass.create(CERTIFICATE, KEY_NOPASS, WWDR_CERTIFICATE, out)
    assert zipfile.is_zipfile(out)


def test_add_file_accepts_bytesio(tmp_path):
    pass_ = ApplePass(
        pass_information=Generic(),
        pass_type_identifier="pass.com.kalvad.test",
        organization_name="Kalvad Test",
        team_identifier="TEAM123456",
    )
    pass_.add_file("icon.png", BytesIO(ICON_PNG))
    out = tmp_path / "bytesio.pkpass"
    pass_.create(CERTIFICATE, KEY, WWDR_CERTIFICATE, out, password=KEY_PASSWORD)
    with zipfile.ZipFile(out) as zf:
        assert zf.read("icon.png") == ICON_PNG
