"""
qr_builder.api
--------------

FastAPI application exposing QR Builder via HTTP.

Entry points (after install):
    qr-builder-api   # convenience wrapper defined in pyproject.toml

Or manually:
    uvicorn qr_builder.api:app --reload
"""

from __future__ import annotations

import io
import logging
import zipfile
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .core import generate_qr, calculate_position

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="QR Builder API",
    description="Generate and embed QR codes into images via HTTP.",
    version="0.1.0",
)

# CORS middleware for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/qr", tags=["qr"])
async def create_qr(
    data: str = Form(..., description="Text or URL to encode."),
    size: int = Form(500, description="Pixel size of the QR image."),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
):
    """Generate a standalone QR code and return as PNG."""
    try:
        img = generate_qr(
            data=data,
            qr_size=size,
            fill_color=fill_color,
            back_color=back_color,
        )
    except Exception as exc:
        logger.exception("Failed to generate QR.")
        raise HTTPException(status_code=400, detail=str(exc))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.post("/embed", tags=["qr"])
async def embed_qr(
    background: UploadFile = File(..., description="Background image file."),
    data: str = Form(..., description="Text or URL to encode."),
    scale: float = Form(0.3, description="Fraction of background width to use for QR."),
    position: str = Form("center"),
    margin: int = Form(20),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
):
    """Embed a QR into an uploaded background image and return the result as PNG."""
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
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Failed to embed QR.")
        raise HTTPException(status_code=500, detail="Internal server error")

    return StreamingResponse(out_buf, media_type="image/png")


@app.post("/batch/embed", tags=["qr"])
async def batch_embed_qr(
    backgrounds: List[UploadFile] = File(..., description="Multiple background images."),
    data: str = Form(..., description="Text or URL to encode."),
    scale: float = Form(0.3, description="Fraction of background width to use for QR."),
    position: str = Form("center"),
    margin: int = Form(20),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
):
    """
    Embed the same QR into multiple uploaded background images and return a ZIP.

    Filenames inside the ZIP will be the original filename with `_qr` appended.
    """
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
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Failed to batch embed QR.")
        raise HTTPException(status_code=500, detail="Internal server error")

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=batch_qr.zip"},
    )


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
