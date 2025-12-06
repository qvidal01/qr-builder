# QR Builder API Documentation

Complete API reference for the QR Builder REST API.

## Base URL

```
http://localhost:8080
```

For production, use your configured domain.

---

## Authentication

Currently no authentication required. For production, consider adding API keys or OAuth.

---

## Endpoints

### Health Check

Check if the server is running.

```
GET /health
```

**Response:**
```json
{
    "status": "ok"
}
```

---

### List Styles

Get all available QR code styles and presets.

```
GET /styles
```

**Response:**
```json
{
    "styles": [
        {"name": "basic", "description": "Simple QR with custom colors", "requires_image": false},
        {"name": "logo", "description": "Logo embedded in QR center", "requires_image": true},
        {"name": "text", "description": "Text/words in QR center", "requires_image": false},
        {"name": "artistic", "description": "Image IS the QR code (colorful)", "requires_image": true},
        {"name": "qart", "description": "Halftone/dithered style", "requires_image": true},
        {"name": "embed", "description": "QR placed on background image", "requires_image": true}
    ],
    "artistic_presets": [
        {"name": "small", "version": 5, "description": "Compact, high contrast"},
        {"name": "medium", "version": 10, "description": "Balanced (default)"},
        {"name": "large", "version": 15, "description": "High detail"},
        {"name": "hd", "version": 20, "description": "Maximum detail"}
    ]
}
```

---

### Basic QR Code

Generate a simple QR code.

```
POST /qr
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `size` | integer | No | 500 | Image size in pixels (100-2000) |
| `fill_color` | string | No | "black" | QR foreground color |
| `back_color` | string | No | "white" | Background color |

**Example:**
```bash
curl -X POST "http://localhost:8080/qr" \
  -F "data=https://example.com" \
  -F "size=400" \
  -F "fill_color=#1a3a5c" \
  --output qr.png
```

**Response:** PNG image

---

### QR with Text

Generate QR code with text in the center.

```
POST /qr/text
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `text` | string | Yes | - | Text to display in center |
| `size` | integer | No | 500 | Image size in pixels |
| `text_scale` | float | No | 0.3 | Text area size (0.1-0.4) |
| `fill_color` | string | No | "black" | QR foreground color |
| `back_color` | string | No | "white" | Background color |
| `font_color` | string | No | "black" | Text color |
| `font_size` | integer | No | auto | Font size in pixels |

**Example:**
```bash
curl -X POST "http://localhost:8080/qr/text" \
  -F "data=https://example.com" \
  -F "text=HELLO" \
  -F "font_color=#e07030" \
  --output qr-text.png
```

**Response:** PNG image

---

### QR with Logo

Generate QR code with logo image in the center.

```
POST /qr/logo
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `logo` | file | Yes | - | Logo image file (PNG/JPG) |
| `size` | integer | No | 500 | Image size in pixels |
| `logo_scale` | float | No | 0.25 | Logo size (0.1-0.4) |
| `fill_color` | string | No | "black" | QR foreground color |
| `back_color` | string | No | "white" | Background color |

**Example:**
```bash
curl -X POST "http://localhost:8080/qr/logo" \
  -F "data=https://example.com" \
  -F "logo=@logo.png" \
  -F "logo_scale=0.3" \
  --output qr-logo.png
```

**Response:** PNG image

---

### Artistic QR

Generate artistic QR where the image IS the QR code.

```
POST /qr/artistic
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `image` | file | Yes | - | Image to transform |
| `preset` | string | No | - | Quality preset: small/medium/large/hd |
| `version` | integer | No | 10 | QR version (1-40) |
| `contrast` | float | No | 1.0 | Image contrast (0.5-2.0) |
| `brightness` | float | No | 1.0 | Image brightness (0.5-2.0) |
| `colorized` | boolean | No | true | Keep colors or B&W |

**Presets:**

| Preset | Version | Contrast | Brightness | Best For |
|--------|---------|----------|------------|----------|
| small | 5 | 1.5 | 1.2 | Small displays, web |
| medium | 10 | 1.3 | 1.1 | General use |
| large | 15 | 1.3 | 1.0 | Print, marketing |
| hd | 20 | 1.2 | 1.0 | Large format |

**Example:**
```bash
curl -X POST "http://localhost:8080/qr/artistic" \
  -F "data=https://example.com" \
  -F "image=@my-image.png" \
  -F "preset=large" \
  --output artistic-qr.png
```

**Response:** PNG image

---

### QArt (Halftone)

Generate halftone/dithered artistic QR code.

```
POST /qr/qart
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `image` | file | Yes | - | Image to transform |
| `version` | integer | No | 10 | QR version (1-40) |
| `point_size` | integer | No | 8 | Point size in pixels |
| `dither` | boolean | No | true | Enable dithering |
| `fast` | boolean | No | false | Fast mode |
| `color_r` | integer | No | 0 | Red component (0-255) |
| `color_g` | integer | No | 0 | Green component (0-255) |
| `color_b` | integer | No | 0 | Blue component (0-255) |

**Example:**
```bash
curl -X POST "http://localhost:8080/qr/qart" \
  -F "data=https://example.com" \
  -F "image=@my-image.png" \
  -F "color_r=26" \
  -F "color_g=58" \
  -F "color_b=92" \
  --output qart.png
```

**Response:** PNG image

---

### Embed QR

Place a QR code on top of a background image.

```
POST /embed
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `background` | file | Yes | - | Background image |
| `scale` | float | No | 0.3 | QR size as fraction of image |
| `position` | string | No | "center" | Position on image |
| `margin` | integer | No | 20 | Margin from edge (pixels) |
| `fill_color` | string | No | "black" | QR foreground color |
| `back_color` | string | No | "white" | QR background color |

**Position options:** `center`, `top-left`, `top-right`, `bottom-left`, `bottom-right`

**Example:**
```bash
curl -X POST "http://localhost:8080/embed" \
  -F "data=https://example.com" \
  -F "background=@flyer.jpg" \
  -F "position=bottom-right" \
  -F "scale=0.2" \
  --output flyer-with-qr.png
```

**Response:** PNG image

---

### Batch Embed

Embed QR into multiple images, returns ZIP.

```
POST /batch/embed
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `backgrounds` | file[] | Yes | - | Multiple background images |
| `scale` | float | No | 0.3 | QR size as fraction |
| `position` | string | No | "center" | Position on images |
| `margin` | integer | No | 20 | Margin from edge |
| `fill_color` | string | No | "black" | QR foreground color |
| `back_color` | string | No | "white" | QR background color |

**Response:** ZIP file containing processed images

---

### Batch Artistic

Generate artistic QR codes from multiple images.

```
POST /batch/artistic
Content-Type: multipart/form-data
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `data` | string | Yes | - | URL or text to encode |
| `images` | file[] | Yes | - | Multiple images |
| `preset` | string | No | "large" | Quality preset |

**Response:** ZIP file containing artistic QR codes

---

## Error Responses

All errors return JSON:

```json
{
    "detail": "Error message here"
}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 422 | Unprocessable entity (missing required field) |
| 500 | Internal server error |

---

## Color Formats

Colors can be specified as:

- **Named colors:** `black`, `white`, `red`, `green`, `blue`, `navy`, `orange`
- **Hex colors:** `#1a3a5c`, `#e07030`
- **RGB (for QArt):** Separate `color_r`, `color_g`, `color_b` parameters

---

## Rate Limits

Currently no rate limits. For production, consider implementing:

- Request rate limiting
- File size limits (default: 10MB)
- Concurrent request limits

---

## CORS

CORS is enabled for all origins by default. For production, configure allowed origins in `server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    # ...
)
```
