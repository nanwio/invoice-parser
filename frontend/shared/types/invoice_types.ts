// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * Invoice data types - SIMPLE and CLEAR
 * Matches backend models exactly for consistency
 */

export interface InvoiceParty {
  name: string;
  tax_id?: string;
  email?: string;
  address?: string;
}

export interface InvoiceLineItem {
  description?: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface InvoiceTax {
  type: 'IVA' | 'IGIC' | 'OTHER' | 'EXEMPT';
  rate: number;
  amount: number;
}

export interface InvoiceFinancials {
  currency?: string;
  subtotal: number;
  tax: InvoiceTax;
  total_amount: number;
}

export interface InvoiceMetadata {
  invoice_number?: string;
  issue_date?: string;
  due_date?: string;
}

export interface Invoice {
  vendor: InvoiceParty;
  customer: InvoiceParty;
  financials: InvoiceFinancials;
  items: InvoiceLineItem[];
  metadata?: InvoiceMetadata;
  notes?: string;
}

// API Response types
export interface InvoiceProcessingResult {
  success: boolean;
  job_id: string;
  invoice_data: Invoice;
  validation: {
    is_valid: boolean;
    errors: string[];
    warnings: string[];
    quality_score: number;
  };
  processing_time_seconds: number;
}

// Upload states
export type UploadStatus =
  | 'idle'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error';

export interface UploadState {
  status: UploadStatus;
  progress: number;
  error?: string;
  result?: InvoiceProcessingResult;
}