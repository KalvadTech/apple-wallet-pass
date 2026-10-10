# ruff: noqa: S324, S303
# Standard Library
import decimal
import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BufferedReader, BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Third Party Stuff
from asn1crypto import cms as asn1_cms
from asn1crypto import core as asn1_core
from asn1crypto import x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from apple_wallet_pass.enums import BarcodeFormat
from apple_wallet_pass.fields import Barcode


@dataclass
class ApplePass:
    """
    Represents an Apple Wallet pass that can be created and signed.

    Required Parameters:
        pass_information: Information specific to the pass type
        pass_type_identifier: Identifier issued by Apple
        organization_name: Name of the organization
        team_identifier: Team identifier issued by Apple
    """

    pass_information: Any
    pass_type_identifier: str
    organization_name: str
    team_identifier: str

    # Required fields with defaults
    serial_number: str = ""
    description: str = ""
    format_version: int = 1

    # Optional fields
    background_color: Optional[str] = None
    foreground_color: Optional[str] = None
    label_color: Optional[str] = None
    logo_text: Optional[str] = None
    barcode: Optional[Barcode] = None
    barcodes: Optional[list] = None
    suppress_strip_shine: bool = False

    # Web Service fields
    web_service_url: Optional[str] = None
    authentication_token: Optional[str] = None

    # Relevance fields
    locations: Optional[list] = None
    ibeacons: Optional[list] = None
    relevant_date: Optional[str] = None

    # Additional fields
    associated_store_identifiers: Optional[list] = None
    app_launch_url: Optional[str] = None
    user_info: Optional[dict] = None
    expiration_date: Optional[str] = None
    voided: Optional[bool] = None

    # Internal storage
    _files: Dict[str, bytes] = field(default_factory=dict)
    _hashes: Dict[str, str] = field(default_factory=dict)

    def add_file(self, name: str, file_data: Union[BytesIO, bytes]) -> None:
        """
        Add a file to be included in the pass package.

        Args:
            name: Name of the file in the pass
            file_data: File content as bytes or BytesIO
        """
        if isinstance(file_data, BytesIO):
            self._files[name] = file_data.read()
        else:
            self._files[name] = file_data

    def create(
        self,
        certificate: Union[str, Path],
        key: Union[str, Path],
        wwdr_certificate: Union[str, Path],
        pass_path: Union[str, Path],
        password: Optional[str] = None,
    ) -> str:
        """
        Create and sign the pass package.

        Args:
            certificate: Path to the signing certificate
            key: Path to the private key
            wwdr_certificate: Path to the WWDR certificate
            password: Optional password for the private key
            pass_path: File path to save the .pkpass file. Defaults to "pass.pkpass"
                      in the current directory.

        Returns:
            String path to the created .pkpass file
        """
        try:
            pass_json = self._create_pass_json()
            manifest = self._create_manifest(pass_json)
            signature = self._create_signature_crypto(
                manifest, certificate, key, wwdr_certificate, password
            )

            self._create_zip(pass_json, manifest, signature, pass_path)
            return str(pass_path)
        except Exception as e:
            raise PassCreationError(f"Failed to create pass: {str(e)}") from e

    def _read_file_bytes(self, path: Union[str, Path]) -> bytes:
        """Read file contents as bytes."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, "rb") as f:
            return f.read()

    def _create_pass_json(self):
        return json.dumps(self, default=pass_handler, ensure_ascii=False)

    def _create_manifest(self, pass_json):
        """
        Creates the hashes for all the files included in the pass file.
        """
        self._hashes["pass.json"] = hashlib.sha1(pass_json.encode("utf-8")).hexdigest()
        for filename, filedata in self._files.items():
            if isinstance(filedata, (bytes, bytearray)):
                data = filedata
            elif isinstance(filedata, (BytesIO, BufferedReader)):
                filedata.seek(0)
                data = filedata.read()
            elif isinstance(filedata, str):
                data = filedata.encode("utf-8")
            else:
                raise TypeError(
                    f"Unsupported file data type for {filename}: {type(filedata)}"
                )
            self._hashes[filename] = hashlib.sha1(data).hexdigest()
        return json.dumps(self._hashes)

    def _create_signature_crypto(
        self, manifest, certificate, key, wwdr_certificate, password
    ):
        """
        Creates a signature (DER encoded) of the manifest.
        The manifest is the file
        containing a list of files included in the pass file (and their hashes).

        Apple mandates a PKCS#7 detached signature using SHA1. cryptography
        >= 40 refuses SHA1 in its PKCS7SignatureBuilder, so the CMS structure
        is assembled with asn1crypto (replicating OpenSSL's output, as pinned
        down by the golden fixtures in tests/) while cryptography performs
        the RSA-SHA1 signature itself, which it still supports.
        """
        cert = x509.load_pem_x509_certificate(self._read_file_bytes(certificate))
        if password is not None:
            password = password.encode("utf-8")
        priv_key = serialization.load_pem_private_key(
            self._read_file_bytes(key), password=password
        )
        wwdr_cert = x509.load_pem_x509_certificate(
            self._read_file_bytes(wwdr_certificate)
        )

        manifest_bytes = manifest.encode("utf-8")

        # The S/MIME capabilities OpenSSL has historically included.
        capabilities = asn1_cms.SMIMECapabilites(
            [
                asn1_cms.SMIMECapabilityIdentifier(
                    {"capability_id": "2.16.840.1.101.3.4.1.42"}  # aes-256-cbc
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {"capability_id": "2.16.840.1.101.3.4.1.22"}  # aes-192-cbc
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {"capability_id": "2.16.840.1.101.3.4.1.2"}  # aes-128-cbc
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {"capability_id": "1.2.840.113549.3.7"}  # des-ede3-cbc
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {
                        "capability_id": "1.2.840.113549.3.2",  # rc2-cbc
                        "parameters": asn1_core.Integer(128),
                    }
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {
                        "capability_id": "1.2.840.113549.3.2",  # rc2-cbc
                        "parameters": asn1_core.Integer(64),
                    }
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {"capability_id": "1.3.14.3.2.7"}  # des-cbc
                ),
                asn1_cms.SMIMECapabilityIdentifier(
                    {
                        "capability_id": "1.2.840.113549.3.2",  # rc2-cbc
                        "parameters": asn1_core.Integer(40),
                    }
                ),
            ]
        )

        signed_attrs = asn1_cms.CMSAttributes(
            [
                asn1_cms.CMSAttribute({"type": "content_type", "values": ["data"]}),
                asn1_cms.CMSAttribute(
                    {
                        "type": "signing_time",
                        "values": [
                            asn1_cms.Time(
                                {
                                    "utc_time": asn1_core.UTCTime(
                                        datetime.now(timezone.utc)
                                    )
                                }
                            )
                        ],
                    }
                ),
                asn1_cms.CMSAttribute(
                    {
                        "type": "message_digest",
                        "values": [hashlib.sha1(manifest_bytes).digest()],
                    }
                ),
                asn1_cms.CMSAttribute(
                    {"type": "smime_capabilities", "values": [capabilities]}
                ),
            ]
        )

        # The signature covers the DER encoding of the signed attributes with
        # the universal SET OF tag (not the [0] tag used inside SignerInfo).
        signature = priv_key.sign(
            signed_attrs.dump(), padding.PKCS1v15(), hashes.SHA1()
        )

        cert_asn1 = asn1_x509.Certificate.load(
            cert.public_bytes(serialization.Encoding.DER)
        )
        wwdr_asn1 = asn1_x509.Certificate.load(
            wwdr_cert.public_bytes(serialization.Encoding.DER)
        )

        signer_info = asn1_cms.SignerInfo(
            {
                "version": "v1",
                "sid": asn1_cms.SignerIdentifier(
                    {
                        "issuer_and_serial_number": asn1_cms.IssuerAndSerialNumber(
                            {
                                "issuer": cert_asn1.issuer,
                                "serial_number": cert_asn1.serial_number,
                            }
                        )
                    }
                ),
                "digest_algorithm": asn1_cms.DigestAlgorithm({"algorithm": "sha1"}),
                "signed_attrs": signed_attrs,
                # rsaEncryption OID, as OpenSSL encodes it here
                "signature_algorithm": asn1_cms.SignedDigestAlgorithm(
                    {"algorithm": "1.2.840.113549.1.1.1"}
                ),
                "signature": signature,
            }
        )

        signed_data = asn1_cms.SignedData(
            {
                "version": "v1",
                "digest_algorithms": [
                    asn1_cms.DigestAlgorithm({"algorithm": "sha1"})
                ],
                # Detached signature: no encapsulated content
                "encap_content_info": asn1_cms.ContentInfo(
                    {"content_type": "data"}
                ),
                "certificates": [
                    asn1_cms.CertificateChoices({"certificate": cert_asn1}),
                    asn1_cms.CertificateChoices({"certificate": wwdr_asn1}),
                ],
                "signer_infos": [signer_info],
            }
        )

        content_info = asn1_cms.ContentInfo(
            {"content_type": "signed_data", "content": signed_data}
        )
        return content_info.dump()

    # Creates .pkpass (zip archive)
    def _create_zip(self, pass_json, manifest, signature, output):
        """Creates .pkpass (zip archive)"""
        zf = zipfile.ZipFile(output, "w")
        zf.writestr("signature", signature)
        zf.writestr("manifest.json", manifest)
        zf.writestr("pass.json", pass_json)
        for filename, filedata in self._files.items():
            if isinstance(filedata, (bytes, bytearray)):
                data = filedata
            elif isinstance(filedata, (BytesIO, BufferedReader)):
                filedata.seek(0)
                data = filedata.read()
            elif isinstance(filedata, str):
                data = filedata.encode("utf-8")
            else:
                raise TypeError(
                    f"Unsupported file data type for {filename}: {type(filedata)}"
                )
            zf.writestr(filename, data)
        zf.close()

    def json_dict(self) -> Dict[str, Any]:
        """Convert the pass to a dictionary suitable for JSON serialization."""
        d = {
            "description": self.description,
            "formatVersion": self.format_version,
            "organizationName": self.organization_name,
            "passTypeIdentifier": self.pass_type_identifier,
            "serialNumber": self.serial_number,
            "teamIdentifier": self.team_identifier,
            "suppressStripShine": self.suppress_strip_shine,
            self.pass_information.jsonname: self.pass_information.json_dict(),
        }

        # Handle barcode formats
        if self.barcode:
            original_formats = {
                BarcodeFormat.PDF417,
                BarcodeFormat.QR,
                BarcodeFormat.AZTEC,
            }
            legacy_barcode = self.barcode
            new_barcodes = [self.barcode.json_dict()]

            if self.barcode._format not in original_formats:
                legacy_barcode = Barcode(
                    message=self.barcode.message,
                    format=BarcodeFormat.PDF417,
                    alt_text=self.barcode.altText,
                )
            d.update({"barcodes": new_barcodes, "barcode": legacy_barcode})

        # Add optional fields if they exist
        optional_fields = {
            "relevantDate": self.relevant_date,
            "backgroundColor": self.background_color,
            "foregroundColor": self.foreground_color,
            "labelColor": self.label_color,
            "logoText": self.logo_text,
            "locations": self.locations,
            "beacons": self.ibeacons,
            "userInfo": self.user_info,
            "associatedStoreIdentifiers": self.associated_store_identifiers,
            "appLaunchURL": self.app_launch_url,
            "expirationDate": self.expiration_date,
        }

        d.update({k: v for k, v in optional_fields.items() if v is not None})

        if self.voided:
            d["voided"] = True

        if self.web_service_url:
            d.update(
                {
                    "webServiceURL": self.web_service_url,
                    "authenticationToken": self.authentication_token,
                }
            )

        return d


class PassCreationError(Exception):
    """Raised when there is an error creating the pass."""

    pass


def pass_handler(obj: Any) -> Any:
    """JSON serialization handler for pass objects."""
    if hasattr(obj, "json_dict"):
        return obj.json_dict()
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    return obj
