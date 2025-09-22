// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * Main invoice upload page - SIMPLE and CLEAN
 * One responsibility: coordinate file upload and display results
 */

'use client';

import { useState } from 'react';
import { FileUpload } from '../../components/upload_form/file_upload';
import { InvoiceViewer } from '../../components/invoice_display/invoice_viewer';
import { InvoiceProcessingResult } from '../../shared/types/invoice_types';
import { isFeatureEnabled } from '../../configuration/app_config';

export function InvoiceUploadPage() {
  const [result, setResult] = useState<InvoiceProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processingMode, setProcessingMode] = useState("fast");

  const handleUploadComplete = (uploadResult: InvoiceProcessingResult) => {
    setResult(uploadResult);
    setError(null);
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
    setResult(null);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="invoice-upload-page">
      <header className="page-header">
        <h1>📄 Invoice Parser</h1>
        <p>Upload your PDF invoice to extract structured data</p>
      </header>

      {/* Processing Mode Selection */}
      {isFeatureEnabled('fastProcessing') && !result && (
        <div className="mode-selection">
          <h3>🎯 Choose Processing Mode:</h3>
          <div className="mode-options">
            <label className="mode-option">
              <input
                type="radio"
                value="lightning"
                checked={processingMode === "lightning"}
                onChange={(e) => setProcessingMode(e.target.value)}
              />
              ⚡ Lightning Mode (~1-2s) - Ultra fast
            </label>
            <label className="mode-option">
              <input
                type="radio"
                value="fast"
                checked={processingMode === "fast"}
                onChange={(e) => setProcessingMode(e.target.value)}
              />
              🚀 Fast Mode (~2-4s) - DONUT + Gemini fallback
            </label>
            <label className="mode-option">
              <input
                type="radio"
                value="enhanced"
                checked={processingMode === "enhanced"}
                onChange={(e) => setProcessingMode(e.target.value)}
              />
              🔍 Enhanced Mode (~5-8s) - Full accuracy
            </label>
          </div>
        </div>
      )}

      {/* Upload Section */}
      {!result && (
        <div className="upload-section">
          <FileUpload
            onUploadComplete={handleUploadComplete}
            onUploadError={handleUploadError}
            processingMode={processingMode}
          />
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-section">
          <div className="error-card">
            <h3>❌ Upload Failed</h3>
            <p>{error}</p>
            <button onClick={handleReset} className="retry-button">
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div className="results-section">
          <div className="results-header">
            <button onClick={handleReset} className="new-upload-button">
              📤 Upload Another Invoice
            </button>
          </div>
          <InvoiceViewer result={result} />
        </div>
      )}

      {/* Instructions */}
      {!result && !error && (
        <div className="instructions">
          <h3>💡 How it works</h3>
          <ol>
            <li>Upload a PDF invoice file</li>
            <li>Our AI extracts structured data</li>
            <li>Review the results and validation</li>
          </ol>
          <p>
            <strong>Supported:</strong> PDF invoices in any language<br />
            <strong>Max size:</strong> 10MB
          </p>
        </div>
      )}
    </div>
  );
}