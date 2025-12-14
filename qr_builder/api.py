"""
qr_builder.api
--------------

FastAPI application exposing QR Builder via HTTP.

Supported endpoints:
- /qr - Basic QR code generation
- /qr/logo - QR with logo in center
- /qr/artistic - Image blended into QR pattern
- /qr/qart - Halftone/dithered style
- /embed - QR placed on background
- /batch/embed - Batch processing
- /webhooks/* - Backend integration endpoints
- /usage/* - Usage tracking for Odoo

Entry points (after install):
    qr-builder-api   # convenience wrapper defined in pyproject.toml

Or manually:
    uvicorn qr_builder.api:app --reload

Integration with aiqso.io:
    Set environment variables:
    - QR_BUILDER_AUTH_ENABLED=true
    - QR_BUILDER_BACKEND_SECRET=your-secret
    - QR_BUILDER_BACKEND_URL=https://api.aiqso.io
    - QR_BUILDER_ALLOWED_ORIGINS=https://aiqso.io,https://www.aiqso.io
"""

from __future__ import annotations

import io
import logging
import zipfile
import tempfile
import time
from pathlib import Path
from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from .core import (
    generate_qr,
    calculate_position,
    generate_qr_with_logo,
    generate_qr_with_text,
    generate_artistic_qr,
    generate_qart,
    QRStyle,
    ARTISTIC_PRESETS,
)

from .auth import (
    UserSession,
    UserTier,
    get_current_user,
    require_auth,
    check_rate_limit,
    require_style,
    verify_backend_webhook,
    session_store,
    get_tier_info,
    get_all_tiers_info,
    ALLOWED_ORIGINS,
    AUTH_ENABLED,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="QR Builder API",
    description="""
Generate and embed QR codes into images via HTTP.

## Authentication

Include your API key in the `X-API-Key` header:
```
X-API-Key: your_api_key_here
```

Get your API key at [aiqso.io/portal](https://aiqso.io/portal)

## Tiers

| Tier | Styles | Daily Limit | Batch |
|------|--------|-------------|-------|
| **Free** | basic, text | 10/day | No |
| **Pro** | All styles | 500/day | 10 images |
| **Business** | All styles | 5000/day | 50 images |

## Available Styles

| Style | Endpoint | Description | Tier |
|-------|----------|-------------|------|
| **Basic** | `/qr` | Simple QR with custom colors | Free |
| **Text** | `/qr/text` | Text/words in QR center | Free |
| **Logo** | `/qr/logo` | Logo embedded in QR center | Pro+ |
| **Artistic** | `/qr/artistic` | Image IS the QR code (colorful) | Pro+ |
| **QArt** | `/qr/qart` | Halftone/dithered style | Pro+ |
| **Embed** | `/embed` | QR placed on background image | Pro+ |

## Presets (Artistic mode)
- `small` - Compact, high contrast (version 5)
- `medium` - Balanced (version 10)
- `large` - High detail (version 15)
- `hd` - Maximum detail (version 20)
    """,
    version="0.3.0",
)

# CORS middleware - configured for aiqso.io
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if AUTH_ENABLED else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*", "X-API-Key", "X-Webhook-Secret"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Required-Tier"],
)


class StyleEnum(str, Enum):
    """Available QR styles for unified endpoint."""
    basic = "basic"
    logo = "logo"
    artistic = "artistic"
    qart = "qart"
    embed = "embed"


class PresetEnum(str, Enum):
    """Artistic mode presets."""
    small = "small"
    medium = "medium"
    large = "large"
    hd = "hd"


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "auth_enabled": AUTH_ENABLED}


@app.get("/styles", tags=["meta"])
async def list_styles(user: UserSession = Depends(get_current_user)) -> dict:
    """List all available QR code styles and presets for current user."""
    user_styles = user.limits.allowed_styles
    all_styles = [
        {"name": "basic", "description": "Simple QR with custom colors", "requires_image": False, "tier": "free"},
        {"name": "text", "description": "Text/words in QR center", "requires_image": False, "tier": "free"},
        {"name": "logo", "description": "Logo embedded in QR center", "requires_image": True, "tier": "pro"},
        {"name": "artistic", "description": "Image IS the QR code (colorful)", "requires_image": True, "tier": "pro"},
        {"name": "qart", "description": "Halftone/dithered style", "requires_image": True, "tier": "pro"},
        {"name": "embed", "description": "QR placed on background image", "requires_image": True, "tier": "pro"},
    ]

    return {
        "styles": [
            {**style, "available": style["name"] in user_styles}
            for style in all_styles
        ],
        "artistic_presets": [
            {"name": "small", "version": 5, "description": "Compact, high contrast"},
            {"name": "medium", "version": 10, "description": "Balanced (default)"},
            {"name": "large", "version": 15, "description": "High detail"},
            {"name": "hd", "version": 20, "description": "Maximum detail"},
        ],
        "user_tier": user.tier.value,
        "custom_colors": user.can_use_custom_colors(),
    }


@app.get("/tiers", tags=["meta"])
async def list_tiers() -> dict:
    """List all available tiers and their features (for pricing page)."""
    return {"tiers": get_all_tiers_info()}


@app.get("/me", tags=["meta"])
async def get_current_user_info(user: UserSession = Depends(get_current_user)) -> dict:
    """Get current user's tier, limits, and usage."""
    return {
        "user_id": user.user_id,
        "tier": user.tier.value,
        "email": user.email,
        "limits": {
            "requests_per_minute": user.limits.requests_per_minute,
            "requests_per_day": user.limits.requests_per_day,
            "max_qr_size": user.limits.max_qr_size,
            "batch_limit": user.limits.batch_limit,
        },
        "usage": {
            "requests_this_minute": user.requests_this_minute,
            "requests_today": user.requests_today,
        },
        "features": {
            "allowed_styles": user.limits.allowed_styles,
            "custom_colors": user.limits.custom_colors,
        },
    }


# =============================================================================
# Basic QR Endpoint
# =============================================================================

@app.post("/qr", tags=["basic"])
async def create_qr(
    data: str = Form(..., description="Text or URL to encode."),
    size: int = Form(500, description="Pixel size of the QR image."),
    fill_color: str = Form("black", description="QR foreground color."),
    back_color: str = Form("white", description="QR background color."),
    user: UserSession = Depends(require_style("basic")),
):
    """Generate a basic standalone QR code and return as PNG. (Free tier)"""
    # Check size limit for tier
    if size > user.limits.max_qr_size:
        raise HTTPException(
            status_code=403,
            detail=f"Size {size} exceeds your tier limit of {user.limits.max_qr_size}px. "
                   f"Upgrade at https://aiqso.io/portal",
        )

    # Check custom colors
    if (fill_color.startswith("#") or back_color.startswith("#")) and not user.can_use_custom_colors():
        raise HTTPException(
            status_code=403,
            detail="Custom hex colors require Pro tier. Upgrade at https://aiqso.io/portal",
        )

    try:
        img = generate_qr(
            data=data,
            qr_size=size,
            fill_color=fill_color,
            back_color=back_color,
        )
    except Exception as exc:
        logger.exception("Failed to generate QR.")
        session_store.log_usage(user.user_id, "basic", False, {"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))

    # Log successful generation
    session_store.log_usage(user.user_id, "basic", True, {"size": size})

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


# =============================================================================
# Logo QR Endpoint
# =============================================================================

@app.post("/qr/logo", tags=["logo"])
async def create_qr_with_logo(
    logo: UploadFile = File(..., description="Logo image to embed in center."),
    data: str = Form(..., description="Text or URL to encode."),
    size: int = Form(500, description="Pixel size of the QR image."),
    logo_scale: float = Form(0.25, description="Logo size as fraction of QR (0.1-0.4)."),
    fill_color: str = Form("black", description="QR foreground color."),
    back_color: str = Form("white", description="QR background color."),
    user: UserSession = Depends(require_style("logo")),
):
    """Generate a QR code with logo embedded in the center. (Pro tier)"""
    # Check size limit
    if size > user.limits.max_qr_size:
        raise HTTPException(
            status_code=403,
            detail=f"Size {size} exceeds your tier limit of {user.limits.max_qr_size}px",
        )

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await logo.read())
            tmp_path = Path(tmp.name)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as out:
            out_path = Path(out.name)

        generate_qr_with_logo(
            data=data,
            logo_path=tmp_path,
            output_path=out_path,
            size=size,
            logo_scale=logo_scale,
            fill_color=fill_color,
            back_color=back_color,
        )

        # Read result and clean up
        with open(out_path, "rb") as f:
            result = f.read()
        tmp_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

    except ValueError as ve:
        session_store.log_usage(user.user_id, "logo", False, {"error": str(ve)})
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception("Failed to generate QR with logo.")
        session_store.log_usage(user.user_id, "logo", False, {"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))

    session_store.log_usage(user.user_id, "logo", True, {"size": size})
    return StreamingResponse(io.BytesIO(result), media_type="image/png")


# =============================================================================
# Text QR Endpoint
# =============================================================================

@app.post("/qr/text", tags=["text"])
async def create_qr_with_text_endpoint(
    text: str = Form(..., description="Text/words to display in center."),
    data: str = Form(..., description="Text or URL to encode."),
    size: int = Form(500, description="Pixel size of the QR image."),
    text_scale: float = Form(0.3, description="Text area size as fraction of QR (0.1-0.4)."),
    fill_color: str = Form("black", description="QR foreground color."),
    back_color: str = Form("white", description="QR background color."),
    font_color: str = Form("black", description="Text color."),
    font_size: int = Form(None, description="Font size in pixels (auto if not set)."),
    user: UserSession = Depends(require_style("text")),
):
    """Generate a QR code with text/words embedded in the center. (Free tier)"""
    # Check size limit
    if size > user.limits.max_qr_size:
        raise HTTPException(
            status_code=403,
            detail=f"Size {size} exceeds your tier limit of {user.limits.max_qr_size}px",
        )

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as out:
            out_path = Path(out.name)

        generate_qr_with_text(
            data=data,
            text=text,
            output_path=out_path,
            size=size,
            text_scale=text_scale,
            fill_color=fill_color,
            back_color=back_color,
            font_color=font_color,
            font_size=font_size,
        )

        with open(out_path, "rb") as f:
            result = f.read()
        out_path.unlink(missing_ok=True)

    except ValueError as ve:
        session_store.log_usage(user.user_id, "text", False, {"error": str(ve)})
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception("Failed to generate QR with text.")
        session_store.log_usage(user.user_id, "text", False, {"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))

    session_store.log_usage(user.user_id, "text", True, {"size": size})
    return StreamingResponse(io.BytesIO(result), media_type="image/png")


# =============================================================================
# Artistic QR Endpoint
# =============================================================================

@app.post("/qr/artistic", tags=["artistic"])
async def create_artistic_qr(
    image: UploadFile = File(..., description="Image to blend into QR pattern."),
    data: str = Form(..., description="Text or URL to encode."),
    preset: Optional[PresetEnum] = Form(None, description="Quality preset (small/medium/large/hd)."),
    version: int = Form(10, description="QR version 1-40 (higher = more detail)."),
    contrast: float = Form(1.0, description="Image contrast (try 1.2-1.5)."),
    brightness: float = Form(1.0, description="Image brightness (try 1.1-1.2)."),
    colorized: bool = Form(True, description="Keep colors (False for B&W)."),
    user: UserSession = Depends(require_style("artistic")),
):
    """
    Generate an artistic QR code where the image IS the QR code. (Pro tier)

    The image is blended into the QR pattern itself, creating a visually
    striking QR code that remains scannable.

    **Recommended presets:**
    - `small` - Compact, good for small displays
    - `medium` - Balanced (default)
    - `large` - High detail, good for print
    - `hd` - Maximum detail, large format
    """
    try:
        # Apply preset
        if preset:
            p = ARTISTIC_PRESETS[preset.value]
            version = p["version"]
            contrast = p["contrast"]
            brightness = p["brightness"]

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await image.read())
            tmp_path = Path(tmp.name)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as out:
            out_path = Path(out.name)

        generate_artistic_qr(
            data=data,
            image_path=tmp_path,
            output_path=out_path,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
            version=version,
        )

        # Read result and clean up
        with open(out_path, "rb") as f:
            result = f.read()
        tmp_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

    except Exception as exc:
        logger.exception("Failed to generate artistic QR.")
        session_store.log_usage(user.user_id, "artistic", False, {"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))

    session_store.log_usage(user.user_id, "artistic", True, {"preset": preset.value if preset else "custom"})
    return StreamingResponse(io.BytesIO(result), media_type="image/png")


# =============================================================================
# QArt Endpoint
# =============================================================================

@app.post("/qr/qart", tags=["qart"])
async def create_qart(
    image: UploadFile = File(..., description="Image to transform into QR."),
    data: str = Form(..., description="Text or URL to encode."),
    version: int = Form(10, description="QR version 1-40."),
    point_size: int = Form(8, description="Point size in pixels."),
    dither: bool = Form(True, description="Use dithering for smoother gradients."),
    fast: bool = Form(False, description="Fast mode (data bits only)."),
    color_r: int = Form(0, description="Red component (0-255)."),
    color_g: int = Form(0, description="Green component (0-255)."),
    color_b: int = Form(0, description="Blue component (0-255)."),
    user: UserSession = Depends(require_style("qart")),
):
    """
    Generate a QArt-style halftone/dithered QR code. (Pro tier)

    Creates a black & white (or single color) artistic QR using dithering
    techniques. Good for minimalist designs.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await image.read())
            tmp_path = Path(tmp.name)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as out:
            out_path = Path(out.name)

        fill_color = None
        if color_r != 0 or color_g != 0 or color_b != 0:
            fill_color = (color_r, color_g, color_b)

        generate_qart(
            data=data,
            image_path=tmp_path,
            output_path=out_path,
            version=version,
            point_size=point_size,
            dither=dither,
            only_data=fast,
            fill_color=fill_color,
        )

        # Read result and clean up
        with open(out_path, "rb") as f:
            result = f.read()
        tmp_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

    except Exception as exc:
        logger.exception("Failed to generate QArt.")
        session_store.log_usage(user.user_id, "qart", False, {"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))

    session_store.log_usage(user.user_id, "qart", True)
    return StreamingResponse(io.BytesIO(result), media_type="image/png")


# =============================================================================
# Embed Endpoint
# =============================================================================

@app.post("/embed", tags=["embed"])
async def embed_qr(
    background: UploadFile = File(..., description="Background image file."),
    data: str = Form(..., description="Text or URL to encode."),
    scale: float = Form(0.3, description="Fraction of background width to use for QR."),
    position: str = Form("center", description="Position: center, top-left, top-right, bottom-left, bottom-right."),
    margin: int = Form(20, description="Margin from edge in pixels."),
    fill_color: str = Form("black", description="QR foreground color."),
    back_color: str = Form("white", description="QR background color."),
    user: UserSession = Depends(require_style("embed")),
):
    """Embed a QR into an uploaded background image and return the result as PNG. (Pro tier)"""
    try:
        raw = await background.read()
        tmp_buf = io.BytesIO(raw)

        from PIL import Image

        bg = Image.open(tmp_buf).convert("RGBA")
        bg_w, bg_h = bg.size

        if not (0 < scale <= 1):
            raise ValueError("scale must be between 0 and 1.")

        qr_size = int(bg_w * scale)
        qr_img = generate_qr(
            data=data,
            qr_size=qr_size,
            fill_color=fill_color,
            back_color=back_color,
        )

        x, y = calculate_position(bg_w, bg_h, qr_size, position, margin)
        bg.paste(qr_img, (x, y), qr_img)

        out_buf = io.BytesIO()
        bg.save(out_buf, format="PNG")
        out_buf.seek(0)

    except ValueError as ve:
        logger.warning("Bad request for /embed: %s", ve)
        session_store.log_usage(user.user_id, "embed", False, {"error": str(ve)})
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Failed to embed QR.")
        session_store.log_usage(user.user_id, "embed", False)
        raise HTTPException(status_code=500, detail="Internal server error")

    session_store.log_usage(user.user_id, "embed", True)
    return StreamingResponse(out_buf, media_type="image/png")


# =============================================================================
# Batch Endpoints
# =============================================================================

@app.post("/batch/embed", tags=["batch"])
async def batch_embed_qr(
    backgrounds: List[UploadFile] = File(..., description="Multiple background images."),
    data: str = Form(..., description="Text or URL to encode."),
    scale: float = Form(0.3, description="Fraction of background width to use for QR."),
    position: str = Form("center"),
    margin: int = Form(20),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
    user: UserSession = Depends(require_style("embed")),
):
    """
    Embed the same QR into multiple uploaded background images and return a ZIP. (Pro tier)

    Filenames inside the ZIP will be the original filename with `_qr` appended.
    """
    # Check batch limit
    if len(backgrounds) > user.get_max_batch_size():
        raise HTTPException(
            status_code=403,
            detail=f"Batch size {len(backgrounds)} exceeds your tier limit of {user.get_max_batch_size()}. "
                   f"Upgrade at https://aiqso.io/portal",
        )

    if user.get_max_batch_size() == 0:
        raise HTTPException(
            status_code=403,
            detail="Batch processing requires Pro or Business tier. Upgrade at https://aiqso.io/portal",
        )

    try:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            from PIL import Image
            for file in backgrounds:
                raw = await file.read()
                tmp_buf = io.BytesIO(raw)
                bg = Image.open(tmp_buf).convert("RGBA")
                bg_w, bg_h = bg.size

                if not (0 < scale <= 1):
                    raise ValueError("scale must be between 0 and 1.")

                qr_size = int(bg_w * scale)
                qr_img = generate_qr(
                    data=data,
                    qr_size=qr_size,
                    fill_color=fill_color,
                    back_color=back_color,
                )

                x, y = calculate_position(bg_w, bg_h, qr_size, position, margin)
                bg.paste(qr_img, (x, y), qr_img)

                out_img_buf = io.BytesIO()
                bg.save(out_img_buf, format="PNG")
                out_img_buf.seek(0)

                name = file.filename or "image.png"
                if "." in name:
                    base, _ = name.rsplit(".", 1)
                    out_name = f"{base}_qr.png"
                else:
                    out_name = f"{name}_qr.png"

                zf.writestr(out_name, out_img_buf.getvalue())

        zip_buf.seek(0)

    except ValueError as ve:
        logger.warning("Bad request for /batch/embed: %s", ve)
        session_store.log_usage(user.user_id, "batch_embed", False, {"error": str(ve)})
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Failed to batch embed QR.")
        session_store.log_usage(user.user_id, "batch_embed", False)
        raise HTTPException(status_code=500, detail="Internal server error")

    session_store.log_usage(user.user_id, "batch_embed", True, {"count": len(backgrounds)})
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=batch_qr.zip"},
    )


@app.post("/batch/artistic", tags=["batch"])
async def batch_artistic_qr(
    images: List[UploadFile] = File(..., description="Multiple images to transform."),
    data: str = Form(..., description="Text or URL to encode."),
    preset: Optional[PresetEnum] = Form(PresetEnum.large, description="Quality preset."),
    user: UserSession = Depends(require_style("artistic")),
):
    """
    Generate artistic QR codes from multiple images and return a ZIP. (Pro tier)
    """
    # Check batch limit
    if len(images) > user.get_max_batch_size():
        raise HTTPException(
            status_code=403,
            detail=f"Batch size {len(images)} exceeds your tier limit of {user.get_max_batch_size()}",
        )

    if user.get_max_batch_size() == 0:
        raise HTTPException(
            status_code=403,
            detail="Batch processing requires Pro or Business tier. Upgrade at https://aiqso.io/portal",
        )

    try:
        p = ARTISTIC_PRESETS[preset.value]
        version = p["version"]
        contrast = p["contrast"]
        brightness = p["brightness"]

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in images:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(await file.read())
                    tmp_path = Path(tmp.name)

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as out:
                    out_path = Path(out.name)

                generate_artistic_qr(
                    data=data,
                    image_path=tmp_path,
                    output_path=out_path,
                    colorized=True,
                    contrast=contrast,
                    brightness=brightness,
                    version=version,
                )

                # Read result
                with open(out_path, "rb") as f:
                    result = f.read()

                # Clean up
                tmp_path.unlink(missing_ok=True)
                out_path.unlink(missing_ok=True)

                name = file.filename or "image.png"
                if "." in name:
                    base, _ = name.rsplit(".", 1)
                    out_name = f"{base}_artistic.png"
                else:
                    out_name = f"{name}_artistic.png"

                zf.writestr(out_name, result)

        zip_buf.seek(0)

    except Exception:
        logger.exception("Failed to batch generate artistic QR.")
        session_store.log_usage(user.user_id, "batch_artistic", False)
        raise HTTPException(status_code=500, detail="Internal server error")

    session_store.log_usage(user.user_id, "batch_artistic", True, {"count": len(images)})
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=batch_artistic_qr.zip"},
    )


# =============================================================================
# Webhook Endpoints (for aiqso.io backend integration)
# =============================================================================

@app.post("/webhooks/update-tier", tags=["webhooks"])
async def webhook_update_tier(
    api_key: str = Body(..., embed=True),
    tier: str = Body(..., embed=True),
    _: bool = Depends(verify_backend_webhook),
):
    """
    Update a user's tier (called from your Odoo/Next.js backend).

    Headers required:
        X-Webhook-Secret: your-backend-secret

    Body:
        {
            "api_key": "user_api_key_here",
            "tier": "pro"  // free, pro, or business
        }
    """
    try:
        new_tier = UserTier(tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    success = session_store.update_user_tier(api_key, new_tier)

    return {
        "success": success,
        "message": f"Tier updated to {tier}" if success else "User session not found (will apply on next request)",
    }


@app.post("/webhooks/invalidate-key", tags=["webhooks"])
async def webhook_invalidate_key(
    api_key: str = Body(..., embed=True),
    _: bool = Depends(verify_backend_webhook),
):
    """
    Invalidate a user's API key (called when subscription is cancelled).

    This removes their session from the cache, forcing re-validation
    on next request.
    """
    if api_key in session_store._sessions:
        del session_store._sessions[api_key]
        return {"success": True, "message": "Session invalidated"}

    return {"success": True, "message": "Session not found (already invalidated)"}


# =============================================================================
# Usage Tracking Endpoints (for Odoo integration)
# =============================================================================

@app.get("/usage/logs", tags=["usage"])
async def get_usage_logs(
    since: float = Query(0, description="Unix timestamp to get logs since"),
    _: bool = Depends(verify_backend_webhook),
):
    """
    Get usage logs since a timestamp (for Odoo sync).

    Your Odoo integration should call this periodically to sync usage data.

    Headers required:
        X-Webhook-Secret: your-backend-secret

    Query params:
        since: Unix timestamp (default 0 = all logs)

    Returns:
        {
            "logs": [
                {
                    "timestamp": 1234567890.123,
                    "user_id": "user_123",
                    "style": "logo",
                    "success": true,
                    "metadata": {"size": 500}
                },
                ...
            ],
            "count": 42,
            "latest_timestamp": 1234567890.123
        }
    """
    logs = session_store.get_usage_since(since)

    return {
        "logs": logs,
        "count": len(logs),
        "latest_timestamp": max((log["timestamp"] for log in logs), default=since),
    }


@app.get("/usage/stats/{user_id}", tags=["usage"])
async def get_user_stats(
    user_id: str,
    _: bool = Depends(verify_backend_webhook),
):
    """
    Get usage statistics for a specific user.

    Headers required:
        X-Webhook-Secret: your-backend-secret

    Returns:
        {
            "user_id": "user_123",
            "total_requests": 42,
            "successful": 40,
            "by_style": {
                "basic": 20,
                "logo": 15,
                "artistic": 5
            }
        }
    """
    stats = session_store.get_user_stats(user_id)
    return {"user_id": user_id, **stats}


@app.post("/usage/cleanup", tags=["usage"])
async def cleanup_old_logs(
    days: int = Body(30, embed=True),
    _: bool = Depends(verify_backend_webhook),
):
    """
    Clean up logs older than N days.

    Call this periodically to prevent memory growth.
    """
    removed = session_store.clear_old_logs(days)
    return {"success": True, "removed_count": removed}


def run() -> None:
    """Convenience entrypoint for `qr-builder-api` script."""
    import os
    import uvicorn

    host = os.getenv("QR_BUILDER_HOST", "0.0.0.0")
    port = int(os.getenv("QR_BUILDER_PORT", "8000"))
    reload = os.getenv("QR_BUILDER_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "qr_builder.api:app",
        host=host,
        port=port,
        reload=reload,
    )
