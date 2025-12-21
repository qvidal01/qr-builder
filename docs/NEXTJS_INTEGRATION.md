# Next.js Integration Guide for your-domain.com

This guide explains how to integrate the QR Builder API with your Next.js website at your-domain.com.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        your-domain.com (Next.js)                       │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React)          │  Backend (API Routes)              │
│  - QR Builder UI           │  - /api/qr-builder/validate-key    │
│  - User Portal             │  - /api/qr-builder/create-key      │
│  - Stripe Checkout         │  - Odoo Integration                │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ API Calls
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QR Builder API (FastAPI)                     │
├─────────────────────────────────────────────────────────────────┤
│  /qr, /qr/logo, /qr/artistic   │  /webhooks/update-tier         │
│  /qr/text, /qr/qart, /embed    │  /usage/logs, /usage/stats     │
└─────────────────────────────────────────────────────────────────┘
```

## Environment Variables

Set these in your QR Builder API deployment:

```bash
# Required for production
QR_BUILDER_AUTH_ENABLED=true
QR_BUILDER_BACKEND_SECRET=your-secure-secret-here
QR_BUILDER_BACKEND_URL=https://api.your-domain.com
QR_BUILDER_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Optional
QR_BUILDER_HOST=0.0.0.0
QR_BUILDER_PORT=8000
```

## Step 1: Backend Endpoint for API Key Validation

Create this endpoint in your Next.js API routes. The QR Builder API will call this to validate user API keys.

```typescript
// pages/api/qr-builder/validate-key.ts (or app/api/qr-builder/validate-key/route.ts)

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_SECRET = process.env.QR_BUILDER_BACKEND_SECRET;

export async function POST(request: NextRequest) {
  // Verify the request is from QR Builder API
  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${BACKEND_SECRET}`) {
    return NextResponse.json({ valid: false, error: 'Unauthorized' }, { status: 401 });
  }

  const { api_key } = await request.json();

  // Look up the API key in your database (Odoo or your user store)
  // This is pseudocode - replace with your actual database logic
  const user = await getUserByApiKey(api_key);

  if (!user) {
    return NextResponse.json({ valid: false, error: 'Invalid API key' });
  }

  // Check if subscription is active
  if (!user.subscriptionActive) {
    return NextResponse.json({ valid: false, error: 'Subscription expired' });
  }

  return NextResponse.json({
    valid: true,
    user_id: user.id,
    tier: user.subscriptionTier, // 'free', 'pro', or 'business'
    email: user.email,
  });
}

// Helper function - implement based on your database
async function getUserByApiKey(apiKey: string) {
  // Example with Odoo:
  // const response = await fetch(`${ODOO_URL}/api/users/by-api-key`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ api_key: apiKey }),
  // });
  // return response.json();

  // Or with Prisma:
  // return prisma.user.findUnique({ where: { apiKey } });

  return null; // Replace with actual implementation
}
```

## Step 2: Generate API Keys for Users

When a user signs up or upgrades, generate an API key for them:

```typescript
// lib/qr-builder.ts

import crypto from 'crypto';

export function generateApiKey(userId: string): string {
  const random = crypto.randomBytes(16).toString('hex');
  return `qrb_${userId}_${random}`;
}

// When user signs up or upgrades
async function onUserSubscribe(userId: string, tier: 'free' | 'pro' | 'business') {
  const apiKey = generateApiKey(userId);

  // Store in your database
  await saveUserApiKey(userId, apiKey, tier);

  return apiKey;
}
```

## Step 3: Frontend QR Builder Component

```tsx
// components/QRBuilder.tsx

'use client';

import { useState } from 'react';

const QR_BUILDER_API = process.env.NEXT_PUBLIC_QR_BUILDER_API || 'https://qr-api.your-domain.com';

interface QRBuilderProps {
  apiKey: string;
  userTier: 'free' | 'pro' | 'business';
}

export function QRBuilder({ apiKey, userTier }: QRBuilderProps) {
  const [data, setData] = useState('');
  const [style, setStyle] = useState('basic');
  const [loading, setLoading] = useState(false);
  const [qrImage, setQrImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Available styles based on tier
  const availableStyles = userTier === 'free'
    ? ['basic', 'text']
    : ['basic', 'text', 'logo', 'artistic', 'qart', 'embed'];

  const generateQR = async () => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('data', data);
      formData.append('size', '500');

      const response = await fetch(`${QR_BUILDER_API}/qr`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate QR');
      }

      const blob = await response.blob();
      setQrImage(URL.createObjectURL(blob));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const generateLogoQR = async (logoFile: File) => {
    if (userTier === 'free') {
      setError('Logo QR requires Pro tier. Upgrade at /portal/upgrade');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('data', data);
      formData.append('logo', logoFile);
      formData.append('size', '500');

      const response = await fetch(`${QR_BUILDER_API}/qr/logo`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey,
        },
        body: formData,
      });

      if (response.status === 403) {
        setError('This feature requires a Pro subscription. Upgrade at /portal/upgrade');
        return;
      }

      if (response.status === 429) {
        setError('Rate limit exceeded. Please wait a moment and try again.');
        return;
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate QR');
      }

      const blob = await response.blob();
      setQrImage(URL.createObjectURL(blob));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="qr-builder">
      <div className="input-section">
        <input
          type="text"
          value={data}
          onChange={(e) => setData(e.target.value)}
          placeholder="Enter URL or text"
        />

        <select value={style} onChange={(e) => setStyle(e.target.value)}>
          {availableStyles.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <button onClick={generateQR} disabled={loading || !data}>
          {loading ? 'Generating...' : 'Generate QR'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {qrImage && (
        <div className="result">
          <img src={qrImage} alt="Generated QR Code" />
          <a href={qrImage} download="qr-code.png">Download</a>
        </div>
      )}

      {userTier === 'free' && (
        <div className="upgrade-prompt">
          Want logo QR codes and more? <a href="/portal/upgrade">Upgrade to Pro</a>
        </div>
      )}
    </div>
  );
}
```

## Step 4: Stripe Webhook for Tier Updates

When a user's subscription changes, update their tier in the QR Builder API:

```typescript
// pages/api/webhooks/stripe.ts

import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);
const QR_BUILDER_API = process.env.QR_BUILDER_API_URL;
const QR_BUILDER_SECRET = process.env.QR_BUILDER_BACKEND_SECRET;

export async function POST(request: NextRequest) {
  const body = await request.text();
  const sig = request.headers.get('stripe-signature')!;

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (err) {
    return NextResponse.json({ error: 'Webhook signature failed' }, { status: 400 });
  }

  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated': {
      const subscription = event.data.object as Stripe.Subscription;
      const tier = getTierFromPriceId(subscription.items.data[0].price.id);
      const apiKey = await getApiKeyForCustomer(subscription.customer as string);

      if (apiKey) {
        // Update tier in QR Builder API
        await fetch(`${QR_BUILDER_API}/webhooks/update-tier`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Webhook-Secret': QR_BUILDER_SECRET!,
          },
          body: JSON.stringify({ api_key: apiKey, tier }),
        });
      }
      break;
    }

    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription;
      const apiKey = await getApiKeyForCustomer(subscription.customer as string);

      if (apiKey) {
        // Downgrade to free or invalidate
        await fetch(`${QR_BUILDER_API}/webhooks/update-tier`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Webhook-Secret': QR_BUILDER_SECRET!,
          },
          body: JSON.stringify({ api_key: apiKey, tier: 'free' }),
        });
      }
      break;
    }
  }

  return NextResponse.json({ received: true });
}

function getTierFromPriceId(priceId: string): string {
  // Map your Stripe price IDs to tiers
  const tierMap: Record<string, string> = {
    'price_pro_monthly': 'pro',
    'price_pro_yearly': 'pro',
    'price_business_monthly': 'business',
    'price_business_yearly': 'business',
  };
  return tierMap[priceId] || 'free';
}

async function getApiKeyForCustomer(customerId: string): Promise<string | null> {
  // Look up in your database
  return null; // Replace with actual implementation
}
```

## Step 5: Odoo Integration for Usage Tracking

Sync usage data from QR Builder to Odoo:

```typescript
// lib/odoo-sync.ts

const QR_BUILDER_API = process.env.QR_BUILDER_API_URL;
const QR_BUILDER_SECRET = process.env.QR_BUILDER_BACKEND_SECRET;

let lastSyncTimestamp = 0;

export async function syncUsageToOdoo() {
  // Get usage logs since last sync
  const response = await fetch(
    `${QR_BUILDER_API}/usage/logs?since=${lastSyncTimestamp}`,
    {
      headers: {
        'X-Webhook-Secret': QR_BUILDER_SECRET!,
      },
    }
  );

  const { logs, latest_timestamp } = await response.json();

  if (logs.length === 0) return;

  // Send to Odoo
  for (const log of logs) {
    await sendToOdoo({
      model: 'qr.usage.log',
      method: 'create',
      args: [{
        user_id: log.user_id,
        style: log.style,
        success: log.success,
        timestamp: new Date(log.timestamp * 1000).toISOString(),
        metadata: JSON.stringify(log.metadata),
      }],
    });
  }

  lastSyncTimestamp = latest_timestamp;

  // Cleanup old logs in QR Builder (optional)
  await fetch(`${QR_BUILDER_API}/usage/cleanup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Webhook-Secret': QR_BUILDER_SECRET!,
    },
    body: JSON.stringify({ days: 7 }), // Keep 7 days in QR Builder
  });
}

// Run this periodically (e.g., cron job every hour)
```

## Step 6: User Portal Page

```tsx
// app/portal/qr-builder/page.tsx

import { getServerSession } from 'next-auth';
import { QRBuilder } from '@/components/QRBuilder';
import { getUserSubscription, getUserApiKey } from '@/lib/user';

export default async function QRBuilderPage() {
  const session = await getServerSession();

  if (!session?.user) {
    return <div>Please sign in to use QR Builder</div>;
  }

  const subscription = await getUserSubscription(session.user.id);
  const apiKey = await getUserApiKey(session.user.id);

  // If no API key, create one
  if (!apiKey) {
    // Redirect to setup or create automatically
  }

  return (
    <div className="portal-page">
      <h1>QR Code Generator</h1>

      <div className="tier-info">
        <p>Current Plan: <strong>{subscription.tier}</strong></p>
        <p>QR Codes Today: {subscription.usageToday} / {subscription.dailyLimit}</p>
        {subscription.tier === 'free' && (
          <a href="/portal/upgrade" className="upgrade-btn">Upgrade for Logo QR</a>
        )}
      </div>

      <QRBuilder apiKey={apiKey} userTier={subscription.tier} />
    </div>
  );
}
```

## API Reference

### QR Generation Endpoints

| Endpoint | Tier | Description |
|----------|------|-------------|
| `POST /qr` | Free | Basic QR code |
| `POST /qr/text` | Free | QR with text overlay |
| `POST /qr/logo` | Pro | QR with logo |
| `POST /qr/artistic` | Pro | Image blended into QR |
| `POST /qr/qart` | Pro | Halftone style |
| `POST /embed` | Pro | QR on background image |
| `POST /batch/embed` | Pro | Batch processing |

### Backend Integration Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /webhooks/update-tier` | X-Webhook-Secret | Update user tier |
| `POST /webhooks/invalidate-key` | X-Webhook-Secret | Invalidate API key |
| `GET /usage/logs` | X-Webhook-Secret | Get usage logs |
| `GET /usage/stats/{user_id}` | X-Webhook-Secret | Get user stats |

### Response Headers

The API includes helpful headers:

- `X-RateLimit-Limit`: Requests allowed per minute
- `X-RateLimit-Remaining`: Requests remaining
- `X-Required-Tier`: Tier needed for blocked features

## Pricing Recommendations

Based on market research:

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Basic + Text QR, 10/day |
| **Pro** | $5/month | All styles, 500/day, batch (10) |
| **Business** | $15/month | All styles, 5000/day, batch (50) |

Or per-QR pricing:
- Basic QR: Free
- Logo QR: $1
- Artistic QR: $2

## Security Checklist

- [ ] Set strong `QR_BUILDER_BACKEND_SECRET`
- [ ] Configure `QR_BUILDER_ALLOWED_ORIGINS` for your domains only
- [ ] Store API keys securely (hashed in database)
- [ ] Implement proper error handling for rate limits
- [ ] Set up monitoring for usage anomalies
- [ ] Use HTTPS for all communications
