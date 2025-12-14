from .core import (
    # Basic functions
    generate_qr,
    generate_qr_only,
    embed_qr_in_image,
    calculate_position,
    validate_data,
    validate_size,
    parse_color,
    # Advanced styles
    generate_qr_with_logo,
    generate_qr_with_text,
    generate_artistic_qr,
    generate_qart,
    # Unified interface
    generate_qr_unified,
    QRConfig,
    QRStyle,
    ARTISTIC_PRESETS,
    # Constants
    MAX_DATA_LENGTH,
    MAX_QR_SIZE,
    MIN_QR_SIZE,
    VALID_POSITIONS,
)

from .auth import (
    UserTier,
    TierLimits,
    UserSession,
    TIER_LIMITS,
    get_all_tiers_info,
    get_tier_info,
)

__version__ = "0.3.0"

__all__ = [
    # Basic functions
    "generate_qr",
    "generate_qr_only",
    "embed_qr_in_image",
    "calculate_position",
    "validate_data",
    "validate_size",
    "parse_color",
    # Advanced styles
    "generate_qr_with_logo",
    "generate_qr_with_text",
    "generate_artistic_qr",
    "generate_qart",
    # Unified interface
    "generate_qr_unified",
    "QRConfig",
    "QRStyle",
    "ARTISTIC_PRESETS",
    # Auth & Tiers
    "UserTier",
    "TierLimits",
    "UserSession",
    "TIER_LIMITS",
    "get_all_tiers_info",
    "get_tier_info",
    # Constants
    "MAX_DATA_LENGTH",
    "MAX_QR_SIZE",
    "MIN_QR_SIZE",
    "VALID_POSITIONS",
    "__version__",
]
