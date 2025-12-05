"""
qr_builder.core
----------------

Core functionality for generating QR codes and embedding them into images.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import qrcode
from PIL import Image

logger = logging.getLogger(__name__)

# Constants for validation
MAX_DATA_LENGTH = 4296  # Maximum characters for QR code
MAX_QR_SIZE = 4000  # Maximum QR image size in pixels
MIN_QR_SIZE = 21  # Minimum QR image size in pixels
VALID_POSITIONS = ("center", "top-left", "top-right", "bottom-left", "bottom-right")


def validate_data(data: str) -> None:
    """Validate QR code data input."""
    if not data or not data.strip():
        raise ValueError("Data cannot be empty.")
    if len(data) > MAX_DATA_LENGTH:
        raise ValueError(f"Data exceeds maximum length of {MAX_DATA_LENGTH} characters.")


def validate_size(size: int) -> None:
    """Validate QR code size."""
    if not MIN_QR_SIZE <= size <= MAX_QR_SIZE:
        raise ValueError(f"Size must be between {MIN_QR_SIZE} and {MAX_QR_SIZE} pixels.")


def generate_qr(
    data: str,
    qr_size: int = 500,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
) -> Image.Image:
    """
    Generate a QR code as a Pillow Image.

    Args:
        data: Text/URL encoded inside the QR.
        qr_size: Final pixel dimensions of QR (square).
        border: Thickness of the QR border.
        fill_color: Foreground color.
        back_color: Background color.

    Returns:
        Pillow Image (RGBA).

    Raises:
        ValueError: If data is empty or exceeds maximum length.
    """
    validate_data(data)
    validate_size(qr_size)
    logger.debug("Generating QR with data=%s", data)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color=fill_color,
        back_color=back_color,
    ).convert("RGBA")

    img = img.resize((qr_size, qr_size), Image.LANCZOS)
    return img


def calculate_position(
    bg_w: int,
    bg_h: int,
    qr_size: int,
    position: str,
    margin: int,
) -> tuple[int, int]:
    """
    Calculate top-left position for a QR on a background.
    """
    position = position.lower()

    if position == "center":
        return (bg_w - qr_size) // 2, (bg_h - qr_size) // 2

    if position == "bottom-right":
        return bg_w - qr_size - margin, bg_h - qr_size - margin

    if position == "bottom-left":
        return margin, bg_h - qr_size - margin

    if position == "top-right":
        return bg_w - qr_size - margin, margin

    if position == "top-left":
        return margin, margin

    raise ValueError(
        f"Unsupported position '{position}'. "
        "Use one of: center, top-left, top-right, bottom-left, bottom-right."
    )


def embed_qr_in_image(
    background_image_path: str | Path,
    data: str,
    output_path: str | Path,
    qr_scale: float = 0.3,
    position: str = "center",
    margin: int = 20,
    fill_color: str = "black",
    back_color: str = "white",
) -> Path:
    """
    Embed a generated QR code inside an existing image.

    Args:
        background_image_path: Path to the background image.
        data: Text/URL encoded into the QR code.
        output_path: File path to save final merged image.
        qr_scale: Fraction of background width used as QR size (0<qr_scale<=1).
        position: Placement (center, top-left, top-right, bottom-left, bottom-right).
        margin: Edge spacing in px.
        fill_color: QR foreground color.
        back_color: QR background color.

    Returns:
        Path: Saved output path.
    """
    logger.info("Embedding QR into image: %s", background_image_path)

    bg_path = Path(background_image_path)
    if not bg_path.exists():
        raise FileNotFoundError(f"Background image not found: {bg_path}")

    bg = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg.size

    if not (0 < qr_scale <= 1):
        raise ValueError("qr_scale must be between 0 and 1.")

    qr_size = int(bg_w * qr_scale)
    qr_img = generate_qr(
        data,
        qr_size=qr_size,
        fill_color=fill_color,
        back_color=back_color,
    )

    x, y = calculate_position(bg_w, bg_h, qr_size, position, margin)
    bg.paste(qr_img, (x, y), qr_img)

    output_path = Path(output_path)
    bg.save(output_path)

    logger.info("Saved merged image to %s", output_path)
    return output_path


def generate_qr_only(
    data: str,
    output_path: str | Path,
    size: int = 500,
    fill_color: str = "black",
    back_color: str = "white",
) -> Path:
    """
    Save a standalone QR code.

    Args:
        data: Content of QR.
        output_path: File path for saving.
        size: Pixel size.
        fill_color: Foreground color.
        back_color: Background color.

    Returns:
        Path: Saved output file.
    """
    logger.debug("Generating standalone QR for data=%s", data)
    img = generate_qr(
        data,
        qr_size=size,
        fill_color=fill_color,
        back_color=back_color,
    )
    output_path = Path(output_path)
    img.save(output_path)
    logger.info("Saved QR-only image: %s", output_path)
    return output_path
