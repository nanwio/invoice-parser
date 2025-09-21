# InvoiceAI SaaS Frontend

A production-ready SaaS frontend for AI-powered invoice processing built with Next.js, Clerk, Supabase, and Stripe.

## 🚀 Features

- **Authentication**: Secure user management with Clerk
- **Database**: PostgreSQL with Supabase and RLS
- **Payments**: Stripe subscription billing
- **AI Processing**: Integration with FastAPI backend
- **Dashboard**: Complete SaaS interface with analytics
- **Multi-tier Plans**: Free, Pro, and Enterprise tiers

## 🏗️ Architecture

```
Frontend (Next.js) ↔ Supabase (Database) ↔ FastAPI (AI Processing)
       ↕                    ↕
   Clerk (Auth)        Stripe (Billing)
```

## 📋 Prerequisites

1. **Clerk Account**: Create at [clerk.com](https://clerk.com)
2. **Supabase Project**: Create at [supabase.com](https://supabase.com)
3. **Stripe Account**: Create at [stripe.com](https://stripe.com)
4. **FastAPI Backend**: Must be running (see backend README)

## 🔧 Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Configuration

Copy `.env.local.example` to `.env.local` and fill in your keys:

```bash
cp .env.local.example .env.local
```

Required environment variables:

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_...

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# FastAPI Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# App Configuration
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### 3. Database Setup

1. **Create Supabase Project**
2. **Run the schema** in Supabase SQL Editor:
   ```sql
   -- Copy and paste contents of supabase-schema.sql
   ```

### 4. Clerk Configuration

1. **Create Clerk Application**
2. **Configure OAuth**: Enable email/password
3. **Setup Webhooks**: Add webhook endpoint:
   - URL: `https://yourdomain.com/api/webhooks/clerk`
   - Events: `user.created`, `user.updated`, `user.deleted`

### 5. Stripe Setup

1. **Create Products**:
   - Pro Plan: €29/month
   - Enterprise Plan: €99/month
2. **Create Webhook Endpoint**:
   - URL: `https://yourdomain.com/api/webhooks/stripe`
   - Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_*`

### 6. FastAPI Backend

Ensure your FastAPI backend is running and accessible. Update JWT auth to accept Clerk tokens.

## 🏃‍♂️ Development

```bash
# Start development server
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
```

## 📊 Database Schema

The application uses the following main tables:

- **users**: User profiles synced from Clerk
- **invoice_processing**: Processing history and results
- **usage_tracking**: Monthly usage statistics
- **subscriptions**: Stripe subscription data
- **api_keys**: Optional API key management

## 🎯 API Integration

### FastAPI Backend Integration

The frontend communicates with the FastAPI backend through:

1. **Authentication Bridge**: Clerk JWT → FastAPI validation
2. **Processing API**: Multiple endpoints for different processing methods
3. **Result Storage**: Automatic saving to Supabase

### Processing Methods

- **Standard**: `POST /api/v1/parse` - Reliable with caching
- **Enhanced**: `POST /api/v1/parse/enhanced` - Professional validation
- **Fast**: `POST /api/v1/parse/fast` - DONUT OCR + Gemini fallback
- **Lightning**: `POST /api/v1/parse/lightning` - Maximum speed

## 💳 Billing Integration

### Plan Limits

| Plan | Monthly Processing | Methods | File Size | Price |
|------|-------------------|---------|-----------|-------|
| Free | 10 | Standard | 10MB | €0 |
| Pro | 500 | All | 25MB | €29 |
| Enterprise | Unlimited | All | 100MB | €99 |

### Subscription Flow

1. User selects plan → Stripe Checkout
2. Webhook updates Supabase → Plan activated
3. Usage tracked → Limits enforced

## 🚀 Deployment

### Vercel (Recommended)

1. **Connect Repository**: Import project to Vercel
2. **Environment Variables**: Add all environment variables
3. **Domain Setup**: Configure custom domain
4. **Deploy**: Automatic deployment on push

### Production Checklist

- [ ] Environment variables configured
- [ ] Database schema deployed
- [ ] Clerk webhooks configured
- [ ] Stripe webhooks configured
- [ ] FastAPI backend deployed
- [ ] DNS configured
- [ ] SSL certificates active

## 📈 Monitoring

### Key Metrics

- User registrations and conversions
- Processing success rates
- Plan upgrade/downgrade events
- API response times
- Error rates

### Analytics Integration

The dashboard includes:
- Real-time usage statistics
- Processing history
- Quality score tracking
- Performance metrics

## 🔒 Security

### Data Protection

- **RLS**: Row Level Security on all tables
- **JWT**: Secure authentication with Clerk
- **HTTPS**: All communications encrypted
- **Input Validation**: File type and size validation

### Privacy

- User data isolated by RLS policies
- Processing results stored securely
- GDPR compliant data handling

## 🐛 Troubleshooting

### Common Issues

1. **Clerk Authentication Fails**
   - Check publishable/secret keys
   - Verify webhook endpoints
   - Ensure correct redirect URLs

2. **Supabase Connection Issues**
   - Verify URL and anon key
   - Check RLS policies
   - Ensure service role key for admin operations

3. **Stripe Webhook Failures**
   - Verify webhook secret
   - Check endpoint accessibility
   - Review webhook event types

4. **FastAPI Integration Problems**
   - Ensure backend is running
   - Check CORS configuration
   - Verify JWT token passing

## 📞 Support

For issues and questions:
- Check the logs in Vercel/Supabase dashboards
- Review webhook delivery in Clerk/Stripe
- Ensure all environment variables are set
- Verify backend API accessibility

## 🔄 Updates

### Version History

- **v1.0.0**: Initial SaaS release
  - Complete authentication flow
  - Multi-tier billing
  - Processing dashboard
  - FastAPI integration

### Roadmap

- [ ] Advanced analytics
- [ ] Team collaboration features
- [ ] API key management
- [ ] Webhook integrations
- [ ] Advanced reporting

## 📝 License

Copyright 2025 Artificial Intelligence Labs, SL. All rights reserved.