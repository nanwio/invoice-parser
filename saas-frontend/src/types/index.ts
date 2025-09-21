// User and authentication types
export interface User {
  id: string;
  clerk_user_id: string;
  email: string;
  plan_type: 'free' | 'pro' | 'enterprise';
  created_at: string;
  updated_at: string;
}

// Invoice processing types
export interface InvoiceProcessing {
  id: string;
  user_id: string;
  file_name: string;
  file_hash: string;
  processing_method: 'standard' | 'enhanced' | 'fast' | 'lightning';
  processing_time_seconds: number;
  quality_score: number;
  success: boolean;
  error_message?: string;
  result_json: any;
  created_at: string;
}

// Usage tracking types
export interface UsageTracking {
  id: string;
  user_id: string;
  month: string;
  total_processed: number;
  successful_processed: number;
  total_processing_time: number;
  updated_at: string;
}

// Subscription types
export interface Subscription {
  id: string;
  user_id: string;
  stripe_subscription_id?: string;
  plan_type: string;
  status: 'active' | 'inactive' | 'canceled' | 'past_due';
  current_period_start?: string;
  current_period_end?: string;
  created_at: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// FastAPI integration types
export interface ParseResult {
  document: {
    hash: string;
    num_pages: number;
    page_size: {
      width: number;
      height: number;
    };
  };
  job: {
    job_id: string;
    job_time: string;
    requested_by: string;
    requested_at: string;
  };
  result: {
    vendor: {
      name: string;
      address?: string;
      tax_id?: string;
    };
    customer?: {
      name: string;
      address?: string;
      tax_id?: string;
    };
    financial_details: {
      total_amount: number;
      currency: string;
      subtotal?: number;
      taxes?: Array<{
        type: string;
        rate: number;
        amount: number;
      }>;
    };
    metadata: {
      invoice_number?: string;
      invoice_date?: string;
      due_date?: string;
    };
    line_items?: Array<{
      description: string;
      quantity: number;
      unit_price: number;
      total_price: number;
    }>;
  };
}

// Enhanced parsing with validation
export interface EnhancedParseResult extends ParseResult {
  validation: {
    is_valid: boolean;
    quality_score: number;
    errors: string[];
    warnings: string[];
    validation_summary: string;
  };
  preprocessing_used: boolean;
}

// Fast parsing with performance metrics
export interface FastParseResult extends ParseResult {
  validation: {
    is_valid: boolean;
    quality_score: number;
    errors: string[];
    warnings: string[];
    validation_summary: string;
  };
  performance: {
    total_time: number;
    method_used: string;
    donut_time?: number;
    gemini_time?: number;
    validation_time?: number;
    donut_success: boolean;
    gemini_fallback: boolean;
  };
}

// Plan configuration
export interface Plan {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  interval: 'month' | 'year';
  features: string[];
  limits: {
    monthly_processing: number;
    processing_methods: Array<'standard' | 'enhanced' | 'fast' | 'lightning'>;
    api_calls: number;
    file_size_mb: number;
  };
  stripe_price_id?: string;
}