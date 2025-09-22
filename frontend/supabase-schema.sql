-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (synced from Clerk)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    plan_type TEXT DEFAULT 'free' CHECK (plan_type IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Invoice processing history
CREATE TABLE invoice_processing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    processing_method TEXT NOT NULL CHECK (processing_method IN ('standard', 'enhanced', 'fast', 'lightning')),
    processing_time_seconds FLOAT,
    quality_score FLOAT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    result_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Usage tracking per month
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    month DATE NOT NULL, -- YYYY-MM-01 format
    total_processed INTEGER DEFAULT 0,
    successful_processed INTEGER DEFAULT 0,
    total_processing_time FLOAT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, month)
);

-- Subscriptions (for Stripe integration)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    plan_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'canceled', 'past_due', 'trialing')),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- API Keys for backend integration (optional)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_clerk_id ON users(clerk_user_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_invoice_processing_user_id ON invoice_processing(user_id);
CREATE INDEX idx_invoice_processing_created_at ON invoice_processing(created_at DESC);
CREATE INDEX idx_invoice_processing_file_hash ON invoice_processing(file_hash);
CREATE INDEX idx_usage_tracking_user_month ON usage_tracking(user_id, month);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_id ON subscriptions(stripe_subscription_id);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- Row Level Security (RLS) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_processing ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON users FOR SELECT USING (auth.uid()::text = clerk_user_id);
CREATE POLICY "Users can update own profile" ON users FOR UPDATE USING (auth.uid()::text = clerk_user_id);

-- Invoice processing policies
CREATE POLICY "Users can view own processing history" ON invoice_processing FOR SELECT USING (
    user_id IN (SELECT id FROM users WHERE clerk_user_id = auth.uid()::text)
);
CREATE POLICY "Users can insert own processing records" ON invoice_processing FOR INSERT WITH CHECK (
    user_id IN (SELECT id FROM users WHERE clerk_user_id = auth.uid()::text)
);

-- Usage tracking policies
CREATE POLICY "Users can view own usage" ON usage_tracking FOR SELECT USING (
    user_id IN (SELECT id FROM users WHERE clerk_user_id = auth.uid()::text)
);
CREATE POLICY "Users can update own usage" ON usage_tracking FOR ALL USING (
    user_id IN (SELECT id FROM users WHERE clerk_user_id = auth.uid()::text)
);

-- Subscription policies
CREATE POLICY "Users can view own subscriptions" ON subscriptions FOR SELECT USING (
    user_id IN (SELECT id FROM users WHERE clerk_user_id = auth.uid()::text)
);

-- API keys policies
CREATE POLICY "Users can manage own API keys" ON api_keys FOR ALL USING (
    user_id IN (SELECT id FROM users WHERE clerk_user_id = auth.uid()::text)
);

-- Functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usage_tracking_updated_at BEFORE UPDATE ON usage_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional)
-- INSERT INTO users (clerk_user_id, email, plan_type) VALUES
-- ('test_user_123', 'test@example.com', 'free');

-- Grant permissions for service role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;