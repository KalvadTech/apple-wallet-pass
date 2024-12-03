from enum import Enum, unique


@unique
class Alignment(str, Enum):
    """Enum for text alignment options in Apple Wallet passes."""

    LEFT = "PKTextAlignmentLeft"
    CENTER = "PKTextAlignmentCenter"
    RIGHT = "PKTextAlignmentRight"
    JUSTIFIED = "PKTextAlignmentJustified"
    NATURAL = "PKTextAlignmentNatural"


@unique
class BarcodeFormat(str, Enum):
    """Enum for supported barcode formats in Apple Wallet passes."""

    PDF417 = "PKBarcodeFormatPDF417"
    QR = "PKBarcodeFormatQR"
    AZTEC = "PKBarcodeFormatAztec"
    CODE128 = "PKBarcodeFormatCode128"


@unique
class TransitType(str, Enum):
    """Enum for transit types in Apple Wallet passes."""

    AIR = "PKTransitTypeAir"
    TRAIN = "PKTransitTypeTrain"
    BUS = "PKTransitTypeBus"
    BOAT = "PKTransitTypeBoat"
    GENERIC = "PKTransitTypeGeneric"


@unique
class DateStyle(str, Enum):
    """Enum for date formatting styles in Apple Wallet passes."""

    NONE = "PKDateStyleNone"
    SHORT = "PKDateStyleShort"
    MEDIUM = "PKDateStyleMedium"
    LONG = "PKDateStyleLong"
    FULL = "PKDateStyleFull"


@unique
class NumberStyle(str, Enum):
    """Enum for number formatting styles in Apple Wallet passes."""

    DECIMAL = "PKNumberStyleDecimal"
    PERCENT = "PKNumberStylePercent"
    SCIENTIFIC = "PKNumberStyleScientific"
    SPELLOUT = "PKNumberStyleSpellOut"
