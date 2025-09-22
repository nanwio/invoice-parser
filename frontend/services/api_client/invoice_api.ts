// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * Invoice API client - SIMPLE and FOCUSED
 * One responsibility: communicate with the invoice processing backend
 */

import { appConfig, getApiUrl } from '../../configuration/app_config';
import { InvoiceProcessingResult } from '../../shared/types/invoice_types';

export class InvoiceAPIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'InvoiceAPIError';
  }
}

export class InvoiceAPIClient {
  /**
   * Simple API client for invoice processing.
   * Easy to use, clear error handling.
   */

  async uploadInvoice(file: File, mode: string = "fast"): Promise<InvoiceProcessingResult> {
    /**
     * Upload and process an invoice PDF file.
     * Returns structured invoice data.
     */
    this._validateFile(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const url = getApiUrl(`/api/v1/upload-invoice?mode=${mode}`);
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(appConfig.api.timeout),
      });

      if (!response.ok) {
        throw new InvoiceAPIError(
          `Upload failed: ${response.statusText}`,
          response.status
        );
      }

      const result = await response.json();
      return result as InvoiceProcessingResult;

    } catch (error) {
      if (error instanceof InvoiceAPIError) {
        throw error;
      }
      throw new InvoiceAPIError('Network error during upload', 0, error);
    }
  }

  async uploadInvoiceFast(file: File): Promise<InvoiceProcessingResult> {
    /**
     * Fast upload and processing for speed-optimized results.
     * Same interface as regular upload but faster processing.
     */
    this._validateFile(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(getApiUrl('/upload-invoice-fast'), {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(appConfig.api.timeout),
      });

      if (!response.ok) {
        throw new InvoiceAPIError(
          `Fast upload failed: ${response.statusText}`,
          response.status
        );
      }

      return await response.json() as InvoiceProcessingResult;

    } catch (error) {
      if (error instanceof InvoiceAPIError) {
        throw error;
      }
      throw new InvoiceAPIError('Network error during fast upload', 0, error);
    }
  }

  private _validateFile(file: File): void {
    /**
     * Validate file before upload.
     * Throws InvoiceAPIError if file is invalid.
     */
    if (!file) {
      throw new InvoiceAPIError('No file provided');
    }

    if (file.size > appConfig.api.maxFileSize) {
      throw new InvoiceAPIError(
        `File too large. Maximum size: ${appConfig.ui.maxFileSizeMB}MB`
      );
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      throw new InvoiceAPIError('Only PDF files are allowed');
    }
  }
}

// Global API client instance - ready to use
export const invoiceAPI = new InvoiceAPIClient();