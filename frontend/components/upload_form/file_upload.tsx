// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * File upload component - SIMPLE and FOCUSED
 * One responsibility: handle PDF file upload with drag & drop
 */

'use client';

import { useState, useCallback } from 'react';
import { UploadState, UploadStatus } from '../../shared/types/invoice_types';
import { invoiceAPI } from '../../services/api_client/invoice_api';

interface FileUploadProps {
  onUploadComplete: (result: any) => void;
  onUploadError: (error: string) => void;
  processingMode?: string;
}

export function FileUpload({ onUploadComplete, onUploadError, processingMode = "fast" }: FileUploadProps) {
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
  });

  const handleFileSelect = useCallback(async (file: File) => {
    if (!file) return;

    setUploadState({ status: 'uploading', progress: 0 });

    try {
      // Simulate progress for user feedback
      setUploadState({ status: 'processing', progress: 50 });

      // Upload and process the file with selected mode
      const result = await invoiceAPI.uploadInvoice(file, processingMode);

      setUploadState({ status: 'completed', progress: 100, result });
      onUploadComplete(result);

    } catch (error: any) {
      const errorMessage = error.message || 'Upload failed';
      setUploadState({ status: 'error', progress: 0, error: errorMessage });
      onUploadError(errorMessage);
    }
  }, [processingMode, onUploadComplete, onUploadError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(file => file.name.toLowerCase().endsWith('.pdf'));

    if (pdfFile) {
      handleFileSelect(pdfFile);
    }
  }, [handleFileSelect]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const isUploading = uploadState.status === 'uploading' || uploadState.status === 'processing';

  return (
    <div className="file-upload-container">
      <div
        className={`upload-area ${isUploading ? 'uploading' : ''}`}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onDragEnter={(e) => e.preventDefault()}
      >
        {isUploading ? (
          <div className="upload-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${uploadState.progress}%` }}
              />
            </div>
            <p>
              {uploadState.status === 'uploading' ? 'Uploading...' : 'Processing...'}
            </p>
          </div>
        ) : (
          <div className="upload-prompt">
            <p>Drag & drop your PDF invoice here</p>
            <p>or</p>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileInputChange}
              disabled={isUploading}
              className="file-input"
            />
            <button className="upload-button" disabled={isUploading}>
              Choose PDF File
            </button>
          </div>
        )}
      </div>

      {uploadState.error && (
        <div className="error-message">
          <p>❌ {uploadState.error}</p>
        </div>
      )}
    </div>
  );
}