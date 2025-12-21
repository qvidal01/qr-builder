#!/usr/bin/env python3
"""
QR Builder Web Server

A simple web interface for generating QR codes with various styles.
Designed for deployment on your AI server.

Usage:
    python server.py
    # Then visit http://localhost:8080

Environment Variables:
    QR_SERVER_HOST - Host to bind (default: 0.0.0.0)
    QR_SERVER_PORT - Port to bind (default: 8080)
"""

import os
import io
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from qr_builder import (
    generate_qr_only,
    generate_qr_with_text,
    generate_qr_with_logo,
    generate_artistic_qr,
    generate_qart,
    ARTISTIC_PRESETS,
)

app = FastAPI(
    title="QR Builder",
    description="Generate beautiful QR codes with logos, text, or artistic styles",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR Builder</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a3a5c 0%, #2d5a87 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
            background: #f0f4f8;
            color: #1a3a5c;
        }
        .tab:hover { background: #e0e8f0; }
        .tab.active {
            background: #1a3a5c;
            color: white;
        }
        .form-section { display: none; }
        .form-section.active { display: block; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        input[type="text"], input[type="url"], input[type="number"], select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #1a3a5c;
        }
        input[type="file"] {
            padding: 10px;
            border: 2px dashed #e0e8f0;
            border-radius: 8px;
            width: 100%;
            cursor: pointer;
        }
        .btn {
            background: linear-gradient(135deg, #e07030 0%, #c05020 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(224, 112, 48, 0.4);
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .result {
            margin-top: 30px;
            text-align: center;
            display: none;
        }
        .result img {
            max-width: 100%;
            border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .result a {
            display: inline-block;
            margin-top: 15px;
            color: #1a3a5c;
            text-decoration: none;
            font-weight: 600;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .row {
            display: flex;
            gap: 15px;
        }
        .row .form-group { flex: 1; }
        .color-input {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .color-input input[type="color"] {
            width: 50px;
            height: 40px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .color-input input[type="text"] {
            flex: 1;
        }
        .description {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }
        footer {
            text-align: center;
            color: rgba(255,255,255,0.7);
            margin-top: 30px;
            font-size: 14px;
        }
        footer a { color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>QR Builder</h1>

        <div class="card">
            <div class="tabs">
                <button class="tab active" data-tab="basic">Basic</button>
                <button class="tab" data-tab="text">With Text</button>
                <button class="tab" data-tab="logo">With Logo</button>
                <button class="tab" data-tab="artistic">Artistic</button>
                <button class="tab" data-tab="qart">QArt</button>
            </div>

            <!-- Basic QR -->
            <form id="form-basic" class="form-section active">
                <div class="form-group">
                    <label>URL or Text to Encode</label>
                    <input type="url" name="data" placeholder="https://example.com" required>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Size (pixels)</label>
                        <input type="number" name="size" value="500" min="100" max="2000">
                    </div>
                    <div class="form-group">
                        <label>QR Color</label>
                        <div class="color-input">
                            <input type="color" name="fill_color_picker" value="#000000">
                            <input type="text" name="fill_color" value="black">
                        </div>
                    </div>
                </div>
                <button type="submit" class="btn">Generate QR Code</button>
            </form>

            <!-- Text QR -->
            <form id="form-text" class="form-section">
                <div class="form-group">
                    <label>URL or Text to Encode</label>
                    <input type="url" name="data" placeholder="https://example.com" required>
                </div>
                <div class="form-group">
                    <label>Text to Display in Center</label>
                    <input type="text" name="text" placeholder="YOUR TEXT" required>
                    <p class="description">This text appears in the center of the QR code</p>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Size (pixels)</label>
                        <input type="number" name="size" value="500" min="100" max="2000">
                    </div>
                    <div class="form-group">
                        <label>Font Color</label>
                        <div class="color-input">
                            <input type="color" name="font_color_picker" value="#1a3a5c">
                            <input type="text" name="font_color" value="#1a3a5c">
                        </div>
                    </div>
                </div>
                <button type="submit" class="btn">Generate QR Code</button>
            </form>

            <!-- Logo QR -->
            <form id="form-logo" class="form-section" enctype="multipart/form-data">
                <div class="form-group">
                    <label>URL or Text to Encode</label>
                    <input type="url" name="data" placeholder="https://example.com" required>
                </div>
                <div class="form-group">
                    <label>Logo Image</label>
                    <input type="file" name="logo" accept="image/*" required>
                    <p class="description">Your logo will be embedded in the center of the QR code</p>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Size (pixels)</label>
                        <input type="number" name="size" value="500" min="100" max="2000">
                    </div>
                    <div class="form-group">
                        <label>Logo Scale</label>
                        <select name="logo_scale">
                            <option value="0.2">Small (20%)</option>
                            <option value="0.25" selected>Medium (25%)</option>
                            <option value="0.3">Large (30%)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn">Generate QR Code</button>
            </form>

            <!-- Artistic QR -->
            <form id="form-artistic" class="form-section" enctype="multipart/form-data">
                <div class="form-group">
                    <label>URL or Text to Encode</label>
                    <input type="url" name="data" placeholder="https://example.com" required>
                </div>
                <div class="form-group">
                    <label>Image to Transform</label>
                    <input type="file" name="image" accept="image/*" required>
                    <p class="description">This image will BE the QR code - blended into the pattern</p>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Quality Preset</label>
                        <select name="preset">
                            <option value="small">Small - Compact</option>
                            <option value="medium">Medium - Balanced</option>
                            <option value="large" selected>Large - High Detail</option>
                            <option value="hd">HD - Maximum Detail</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Color Mode</label>
                        <select name="colorized">
                            <option value="true" selected>Colorized</option>
                            <option value="false">Black & White</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn">Generate Artistic QR</button>
            </form>

            <!-- QArt -->
            <form id="form-qart" class="form-section" enctype="multipart/form-data">
                <div class="form-group">
                    <label>URL or Text to Encode</label>
                    <input type="url" name="data" placeholder="https://example.com" required>
                </div>
                <div class="form-group">
                    <label>Image to Transform</label>
                    <input type="file" name="image" accept="image/*" required>
                    <p class="description">Creates a halftone/dithered artistic QR code</p>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>QR Color</label>
                        <div class="color-input">
                            <input type="color" name="color_picker" value="#1a3a5c">
                            <input type="text" name="color" value="#1a3a5c">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Dithering</label>
                        <select name="dither">
                            <option value="true" selected>Enabled (smoother)</option>
                            <option value="false">Disabled</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn">Generate QArt Code</button>
            </form>

            <div class="loading">Generating your QR code...</div>

            <div class="result">
                <img id="result-image" src="" alt="Generated QR Code">
                <br>
                <a id="download-link" href="" download="qr-code.png">Download QR Code</a>
            </div>
        </div>

        <footer>
            Powered by <a href="https://github.com/qvidal01/qr-builder">QR Builder</a> |
            Your Company
        </footer>
    </div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.form-section').forEach(f => f.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('form-' + tab.dataset.tab).classList.add('active');
                document.querySelector('.result').style.display = 'none';
            });
        });

        // Color picker sync
        document.querySelectorAll('input[type="color"]').forEach(picker => {
            const textInput = picker.parentElement.querySelector('input[type="text"]');
            picker.addEventListener('input', () => textInput.value = picker.value);
            textInput.addEventListener('input', () => picker.value = textInput.value);
        });

        // Form submission
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData(form);
                const tabId = form.id.replace('form-', '');
                const btn = form.querySelector('.btn');
                const loading = document.querySelector('.loading');
                const result = document.querySelector('.result');

                btn.disabled = true;
                loading.style.display = 'block';
                result.style.display = 'none';

                try {
                    const response = await fetch('/generate/' + tabId, {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Generation failed');
                    }

                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);

                    document.getElementById('result-image').src = url;
                    document.getElementById('download-link').href = url;
                    result.style.display = 'block';
                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    btn.disabled = false;
                    loading.style.display = 'none';
                }
            });
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the web interface."""
    return HTML_TEMPLATE


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/generate/basic")
async def generate_basic(
    data: str = Form(...),
    size: int = Form(500),
    fill_color: str = Form("black"),
):
    """Generate basic QR code."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        generate_qr_only(
            data=data,
            output_path=tmp_path,
            size=size,
            fill_color=fill_color,
        )

        with open(tmp_path, "rb") as f:
            result = f.read()
        tmp_path.unlink(missing_ok=True)

        return StreamingResponse(io.BytesIO(result), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/text")
async def generate_text(
    data: str = Form(...),
    text: str = Form(...),
    size: int = Form(500),
    font_color: str = Form("black"),
):
    """Generate QR code with text in center."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        generate_qr_with_text(
            data=data,
            text=text,
            output_path=tmp_path,
            size=size,
            font_color=font_color,
        )

        with open(tmp_path, "rb") as f:
            result = f.read()
        tmp_path.unlink(missing_ok=True)

        return StreamingResponse(io.BytesIO(result), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/logo")
async def generate_logo(
    data: str = Form(...),
    logo: UploadFile = File(...),
    size: int = Form(500),
    logo_scale: float = Form(0.25),
):
    """Generate QR code with logo in center."""
    try:
        # Save uploaded logo
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await logo.read())
            logo_path = Path(tmp.name)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            out_path = Path(tmp.name)

        generate_qr_with_logo(
            data=data,
            logo_path=logo_path,
            output_path=out_path,
            size=size,
            logo_scale=logo_scale,
        )

        with open(out_path, "rb") as f:
            result = f.read()
        logo_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

        return StreamingResponse(io.BytesIO(result), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/artistic")
async def generate_artistic(
    data: str = Form(...),
    image: UploadFile = File(...),
    preset: str = Form("large"),
    colorized: str = Form("true"),
):
    """Generate artistic QR code where image IS the QR."""
    try:
        # Save uploaded image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await image.read())
            image_path = Path(tmp.name)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            out_path = Path(tmp.name)

        # Get preset values
        p = ARTISTIC_PRESETS.get(preset, ARTISTIC_PRESETS["large"])

        generate_artistic_qr(
            data=data,
            image_path=image_path,
            output_path=out_path,
            colorized=(colorized.lower() == "true"),
            contrast=p["contrast"],
            brightness=p["brightness"],
            version=p["version"],
        )

        with open(out_path, "rb") as f:
            result = f.read()
        image_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

        return StreamingResponse(io.BytesIO(result), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/qart")
async def generate_qart_endpoint(
    data: str = Form(...),
    image: UploadFile = File(...),
    color: str = Form("#000000"),
    dither: str = Form("true"),
):
    """Generate QArt halftone/dithered QR code."""
    try:
        # Save uploaded image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await image.read())
            image_path = Path(tmp.name)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            out_path = Path(tmp.name)

        # Parse color
        fill_color = None
        if color and color != "#000000":
            c = color.lstrip("#")
            fill_color = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

        generate_qart(
            data=data,
            image_path=image_path,
            output_path=out_path,
            dither=(dither.lower() == "true"),
            fill_color=fill_color,
        )

        with open(out_path, "rb") as f:
            result = f.read()
        image_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

        return StreamingResponse(io.BytesIO(result), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the server."""
    import uvicorn

    host = os.getenv("QR_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("QR_SERVER_PORT", "8080"))

    print(f"Starting QR Builder server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
