# QR Builder - WordPress Integration Guide

This guide explains how to add the QR Builder widget to your WordPress website.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Server Setup](#server-setup)
4. [WordPress Installation](#wordpress-installation)
5. [Configuration](#configuration)
6. [Customization](#customization)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The QR Builder widget allows your WordPress visitors to generate QR codes directly on your website. It supports multiple styles:

| Style | Description |
|-------|-------------|
| **Basic** | Simple QR code with custom colors |
| **With Text** | QR code with text/words in the center |
| **With Logo** | QR code with uploaded logo in center |
| **Artistic** | Image transforms INTO the QR code pattern |

---

## Prerequisites

Before installing the widget, you need:

1. **A server running QR Builder** (VPS, cloud server, or local)
2. **Python 3.9+** installed on that server
3. **WordPress admin access**
4. **Ability to add Custom HTML** (Gutenberg, Elementor, or theme)

---

## Server Setup

### Option 1: Quick Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/AIQSO/qr-builder.git
cd qr-builder

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -e .

# 4. Run the server
python server.py
```

The server will start at `http://0.0.0.0:8080`

### Option 2: Docker Setup

```bash
# Build and run
docker build -t qr-builder .
docker run -d -p 8080:8080 --name qr-builder qr-builder python server.py
```

### Option 3: Production with Systemd

Create `/etc/systemd/system/qr-builder.service`:

```ini
[Unit]
Description=QR Builder Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/qr-builder
Environment=QR_SERVER_HOST=0.0.0.0
Environment=QR_SERVER_PORT=8080
ExecStart=/opt/qr-builder/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable qr-builder
sudo systemctl start qr-builder
```

### Configure Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name qr.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # For file uploads
        client_max_body_size 10M;
    }
}
```

### SSL with Let's Encrypt

```bash
sudo certbot --nginx -d qr.yourdomain.com
```

---

## WordPress Installation

### Method 1: Gutenberg Block (Recommended)

1. Edit the page/post where you want the QR Builder
2. Add a **Custom HTML** block
3. Copy the contents of `qr-builder-widget.html`
4. Paste into the Custom HTML block
5. **Update the API URL** (see Configuration below)
6. Publish/Update the page

### Method 2: Elementor

1. Edit page with Elementor
2. Add **HTML** widget
3. Paste the widget code
4. Update the API URL
5. Save

### Method 3: Classic Editor

1. Switch to **Text** mode (not Visual)
2. Paste the widget code
3. Update the API URL
4. Publish

### Method 4: Theme Files (Advanced)

Add to your theme's `functions.php`:

```php
function qr_builder_shortcode() {
    ob_start();
    include get_template_directory() . '/qr-builder-widget.html';
    return ob_get_clean();
}
add_shortcode('qr_builder', 'qr_builder_shortcode');
```

Then use `[qr_builder]` shortcode in any page.

---

## Configuration

### Essential: Update the API URL

Find this line in the widget code (around line 280):

```javascript
const QR_API_URL = 'http://localhost:8080';
```

Change it to your server's URL:

```javascript
const QR_API_URL = 'https://qr.yourdomain.com';
```

### Environment Variables (Server)

| Variable | Default | Description |
|----------|---------|-------------|
| `QR_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `QR_SERVER_PORT` | `8080` | Server port |

---

## Customization

### Change Colors

At the top of the widget CSS, modify these variables:

```css
#qr-builder-widget {
    --qr-primary: #1a3a5c;    /* Main blue color */
    --qr-secondary: #e07030;  /* Orange button color */
    --qr-bg: #f8fafc;         /* Background */
    --qr-card: #ffffff;       /* Card background */
    --qr-text: #333333;       /* Text color */
    --qr-border: #e0e8f0;     /* Border color */
}
```

### Change Title

Find and modify:

```html
<h2 class="qrb-title">QR Code Generator</h2>
```

### Remove a Tab

To remove a style option, delete both:
1. The tab button: `<button class="qrb-tab" data-tab="artistic">Artistic</button>`
2. The form: `<form class="qrb-form" id="qrb-form-artistic">...</form>`

### Change Default Sizes

Modify the `<select>` options in each form:

```html
<select class="qrb-select" name="size">
    <option value="300">Small (300px)</option>
    <option value="500" selected>Medium (500px)</option>
    <option value="800">Large (800px)</option>
</select>
```

---

## Troubleshooting

### "Failed to generate QR code"

1. **Check server is running:**
   ```bash
   curl http://your-server:8080/health
   # Should return: {"status":"ok"}
   ```

2. **Check CORS:** Server already has CORS enabled, but verify your domain isn't blocked

3. **Check console:** Open browser DevTools (F12) → Console for errors

### Widget not displaying

1. Ensure Custom HTML block is used (not paragraph/text)
2. Check for JavaScript errors in console
3. Verify no conflicting CSS from your theme

### File upload fails

1. Check server allows file uploads (`client_max_body_size` in Nginx)
2. Verify file is valid image (PNG, JPG)
3. Check file isn't too large (recommended: under 5MB)

### CORS errors

If you see "Access-Control-Allow-Origin" errors:

1. Verify server.py is running (it has CORS enabled)
2. Check your reverse proxy isn't stripping CORS headers
3. Ensure API URL uses same protocol (http/https) as your WordPress site

### Mixed content warnings

If your WordPress is HTTPS, your QR server must also be HTTPS:

```javascript
// Wrong (will fail on HTTPS WordPress):
const QR_API_URL = 'http://qr.yourdomain.com';

// Correct:
const QR_API_URL = 'https://qr.yourdomain.com';
```

---

## API Endpoints Reference

The widget uses these server endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate/basic` | POST | Basic QR code |
| `/generate/text` | POST | QR with text |
| `/generate/logo` | POST | QR with logo |
| `/generate/artistic` | POST | Artistic QR |
| `/health` | GET | Health check |

### Parameters

**Basic:**
- `data` (required): URL or text to encode
- `size`: Pixel size (default: 500)
- `fill_color`: QR color (default: black)

**Text:**
- `data` (required): URL or text to encode
- `text` (required): Center text
- `size`: Pixel size
- `font_color`: Text color

**Logo:**
- `data` (required): URL or text to encode
- `logo` (required): Image file
- `size`: Pixel size
- `logo_scale`: Logo size ratio (0.1-0.4)

**Artistic:**
- `data` (required): URL or text to encode
- `image` (required): Image file
- `preset`: small/medium/large/hd
- `colorized`: true/false

---

## Support

- **GitHub Issues:** https://github.com/AIQSO/qr-builder/issues
- **Documentation:** https://github.com/AIQSO/qr-builder

---

## License

MIT License - Free for personal and commercial use.
