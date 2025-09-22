// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * Invoice display component - SIMPLE and FOCUSED
 * One responsibility: show structured invoice data in a readable format
 */

'use client';

import { Invoice, InvoiceProcessingResult } from '../../shared/types/invoice_types';

interface InvoiceViewerProps {
  result: InvoiceProcessingResult;
}

export function InvoiceViewer({ result }: InvoiceViewerProps) {
  const { invoice_data, validation, processing_time_seconds } = result;

  return (
    <div className="invoice-viewer">
      {/* Processing Info */}
      <div className="processing-info">
        <h3>📄 Invoice Processed Successfully</h3>
        <p>⏱️ Processing time: {processing_time_seconds.toFixed(2)}s</p>
        <p>✅ Quality Score: {validation.quality_score.toFixed(1)}/100</p>
      </div>

      {/* Validation Results */}
      {(validation.errors.length > 0 || validation.warnings.length > 0) && (
        <div className="validation-results">
          {validation.errors.length > 0 && (
            <div className="errors">
              <h4>❌ Errors:</h4>
              <ul>
                {validation.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {validation.warnings.length > 0 && (
            <div className="warnings">
              <h4>⚠️ Warnings:</h4>
              <ul>
                {validation.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Invoice Data */}
      <div className="invoice-data">
        <InvoiceBasicInfo invoice={invoice_data} />
        <InvoiceParties invoice={invoice_data} />
        <InvoiceFinancials invoice={invoice_data} />
        <InvoiceLineItems invoice={invoice_data} />
      </div>
    </div>
  );
}

function InvoiceBasicInfo({ invoice }: { invoice: Invoice }) {
  return (
    <div className="basic-info">
      <h3>📋 Invoice Information</h3>
      {invoice.metadata && (
        <div className="metadata">
          {invoice.metadata.invoice_number && (
            <p><strong>Invoice #:</strong> {invoice.metadata.invoice_number}</p>
          )}
          {invoice.metadata.issue_date && (
            <p><strong>Date:</strong> {invoice.metadata.issue_date}</p>
          )}
          {invoice.metadata.due_date && (
            <p><strong>Due Date:</strong> {invoice.metadata.due_date}</p>
          )}
        </div>
      )}
    </div>
  );
}

function InvoiceParties({ invoice }: { invoice: Invoice }) {
  return (
    <div className="parties">
      <div className="vendor">
        <h4>🏢 Vendor</h4>
        <p><strong>Name:</strong> {invoice.vendor.name}</p>
        {invoice.vendor.tax_id && <p><strong>Tax ID:</strong> {invoice.vendor.tax_id}</p>}
        {invoice.vendor.email && <p><strong>Email:</strong> {invoice.vendor.email}</p>}
      </div>

      <div className="customer">
        <h4>👤 Customer</h4>
        <p><strong>Name:</strong> {invoice.customer.name}</p>
        {invoice.customer.tax_id && <p><strong>Tax ID:</strong> {invoice.customer.tax_id}</p>}
      </div>
    </div>
  );
}

function InvoiceFinancials({ invoice }: { invoice: Invoice }) {
  const { financials } = invoice;

  return (
    <div className="financials">
      <h4>💰 Financial Summary</h4>
      <div className="amounts">
        <p><strong>Subtotal:</strong> {financials.subtotal} {financials.currency || ''}</p>
        <p><strong>Tax ({financials.tax.type}):</strong> {financials.tax.amount} ({financials.tax.rate}%)</p>
        <p className="total"><strong>Total:</strong> {financials.total_amount} {financials.currency || ''}</p>
      </div>
    </div>
  );
}

function InvoiceLineItems({ invoice }: { invoice: Invoice }) {
  return (
    <div className="line-items">
      <h4>📝 Line Items</h4>
      <div className="items-table">
        {invoice.items.map((item, index) => (
          <div key={index} className="item-row">
            <div className="item-description">
              {item.description || `Item ${index + 1}`}
            </div>
            <div className="item-quantity">Qty: {item.quantity}</div>
            <div className="item-price">Unit: {item.unit_price}</div>
            <div className="item-total">Total: {item.line_total}</div>
          </div>
        ))}
      </div>
    </div>
  );
}