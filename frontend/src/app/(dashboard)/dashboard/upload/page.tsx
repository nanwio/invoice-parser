'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '@clerk/nextjs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  Zap,
  Target,
  AlertCircle,
} from 'lucide-react';
import { useUser } from '@/hooks/useUser';
import { invoiceApi, ApiError } from '@/lib/api';
import { getUserPlanLimits, canUserProcess } from '@/lib/plans';
import { supabase, dbHelpers } from '@/lib/supabase';

type ProcessingMethod = 'standard' | 'enhanced' | 'fast' | 'lightning';

interface ProcessingResult {
  success: boolean;
  data?: any;
  error?: string;
  processingTime?: number;
  method?: ProcessingMethod;
}

const PROCESSING_METHODS = {
  standard: {
    name: 'Standard',
    description: 'Reliable processing with caching',
    icon: FileText,
    color: 'blue',
    estimatedTime: '2-5s',
    features: ['Document classification', 'Smart caching', 'Basic validation'],
  },
  enhanced: {
    name: 'Enhanced',
    description: 'Professional validation with preprocessing',
    icon: Shield,
    color: 'green',
    estimatedTime: '3-8s',
    features: ['Image preprocessing', 'Quality scoring', 'Mathematical validation'],
  },
  fast: {
    name: 'Fast',
    description: 'DONUT OCR with Gemini fallback',
    icon: Zap,
    color: 'orange',
    estimatedTime: '<5s',
    features: ['Hybrid processing', 'Performance metrics', 'Automatic fallback'],
  },
  lightning: {
    name: 'Lightning',
    description: 'Maximum speed optimization',
    icon: Target,
    color: 'purple',
    estimatedTime: '<3s',
    features: ['Pre-loaded models', 'Cache-first approach', 'Parallel validation'],
  },
};

export default function UploadPage() {
  const { dbUser } = useUser();
  const { getToken } = useAuth();
  const [selectedMethod, setSelectedMethod] = useState<ProcessingMethod>('standard');
  const [usePreprocessing, setUsePreprocessing] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const planLimits = getUserPlanLimits(dbUser?.plan_type || 'free');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      setResult(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    maxSize: planLimits.file_size_mb * 1024 * 1024,
  });

  const handleProcess = async () => {
    if (!uploadedFile || !dbUser) return;

    try {
      setProcessing(true);
      setResult(null);

      // Check if user can process
      const currentMonth = new Date().toISOString().slice(0, 7) + '-01';
      const { data: usage } = await supabase
        .from('usage_tracking')
        .select('total_processed')
        .eq('user_id', dbUser.id)
        .eq('month', currentMonth)
        .single();

      const currentUsage = usage?.total_processed || 0;

      if (!canUserProcess(dbUser.plan_type, currentUsage, selectedMethod)) {
        throw new Error('Plan limits exceeded. Please upgrade your plan.');
      }

      const startTime = Date.now();
      let response;

      // Call appropriate API based on method
      switch (selectedMethod) {
        case 'standard':
          response = await invoiceApi.parseStandard(uploadedFile, getToken);
          break;
        case 'enhanced':
          response = await invoiceApi.parseEnhanced(uploadedFile, getToken, usePreprocessing);
          break;
        case 'fast':
          response = await invoiceApi.parseFast(uploadedFile, getToken);
          break;
        case 'lightning':
          response = await invoiceApi.parseLightning(uploadedFile, getToken);
          break;
        default:
          throw new Error('Invalid processing method');
      }

      const processingTime = (Date.now() - startTime) / 1000;

      // Record processing in database
      await dbHelpers.recordProcessing({
        user_id: dbUser.id,
        file_name: uploadedFile.name,
        file_hash: response.document.hash,
        processing_method: selectedMethod,
        processing_time_seconds: processingTime,
        quality_score: response.validation?.quality_score || 0,
        success: true,
        result_json: response,
      });

      // Update usage tracking
      await dbHelpers.updateUsageTracking(dbUser.id, currentMonth);

      setResult({
        success: true,
        data: response,
        processingTime,
        method: selectedMethod,
      });
    } catch (error) {
      console.error('Processing error:', error);

      let errorMessage = 'An unexpected error occurred';
      if (error instanceof ApiError) {
        errorMessage = error.message;
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      // Record failed processing
      if (dbUser && uploadedFile) {
        try {
          await dbHelpers.recordProcessing({
            user_id: dbUser.id,
            file_name: uploadedFile.name,
            file_hash: 'error',
            processing_method: selectedMethod,
            processing_time_seconds: 0,
            quality_score: 0,
            success: false,
            error_message: errorMessage,
            result_json: {},
          });
        } catch (dbError) {
          console.error('Failed to record error:', dbError);
        }
      }

      setResult({
        success: false,
        error: errorMessage,
        method: selectedMethod,
      });
    } finally {
      setProcessing(false);
    }
  };

  const isMethodAvailable = (method: ProcessingMethod) => {
    return planLimits.processing_methods.includes(method);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload Invoice</h1>
        <p className="text-gray-600 mt-1">
          Upload a PDF invoice and choose your processing method.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Area */}
        <Card>
          <CardHeader>
            <CardTitle>File Upload</CardTitle>
            <CardDescription>
              Select a PDF invoice to process (max {planLimits.file_size_mb}MB)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              {isDragActive ? (
                <p className="text-lg text-blue-600">Drop the PDF here...</p>
              ) : (
                <div>
                  <p className="text-lg text-gray-600 mb-2">
                    Drop your PDF here, or click to select
                  </p>
                  <p className="text-sm text-gray-500">
                    PDF files only, up to {planLimits.file_size_mb}MB
                  </p>
                </div>
              )}
            </div>

            {uploadedFile && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  <span className="font-medium">{uploadedFile.name}</span>
                  <Badge variant="secondary">
                    {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Processing Options */}
        <Card>
          <CardHeader>
            <CardTitle>Processing Method</CardTitle>
            <CardDescription>
              Choose the processing strategy that fits your needs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={selectedMethod} onValueChange={(value) => setSelectedMethod(value as ProcessingMethod)}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="standard" disabled={!isMethodAvailable('standard')}>
                  Standard
                </TabsTrigger>
                <TabsTrigger value="enhanced" disabled={!isMethodAvailable('enhanced')}>
                  Enhanced
                </TabsTrigger>
              </TabsList>
              <TabsList className="grid w-full grid-cols-2 mt-2">
                <TabsTrigger value="fast" disabled={!isMethodAvailable('fast')}>
                  Fast
                </TabsTrigger>
                <TabsTrigger value="lightning" disabled={!isMethodAvailable('lightning')}>
                  Lightning
                </TabsTrigger>
              </TabsList>

              {Object.entries(PROCESSING_METHODS).map(([key, method]) => (
                <TabsContent key={key} value={key} className="mt-4">
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <method.icon className={`h-5 w-5 text-${method.color}-600`} />
                      <span className="font-medium">{method.name}</span>
                      <Badge variant="outline">{method.estimatedTime}</Badge>
                      {!isMethodAvailable(key as ProcessingMethod) && (
                        <Badge variant="destructive">Pro Plan Required</Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600">{method.description}</p>
                    <div className="space-y-1">
                      {method.features.map((feature, index) => (
                        <div key={index} className="flex items-center space-x-2 text-sm">
                          <CheckCircle className="h-3 w-3 text-green-600" />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>

                    {key === 'enhanced' && (
                      <div className="space-y-2">
                        <Label htmlFor="preprocessing">Advanced Options</Label>
                        <Select
                          value={usePreprocessing.toString()}
                          onValueChange={(value) => setUsePreprocessing(value === 'true')}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="true">With Image Preprocessing</SelectItem>
                            <SelectItem value="false">Skip Preprocessing (Faster)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                </TabsContent>
              ))}
            </Tabs>

            <Button
              onClick={handleProcess}
              disabled={!uploadedFile || processing || !isMethodAvailable(selectedMethod)}
              className="w-full mt-6"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Process Invoice
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              {result.success ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
              <span>Processing Results</span>
              {result.processingTime && (
                <Badge variant="outline">
                  <Clock className="h-3 w-3 mr-1" />
                  {result.processingTime.toFixed(2)}s
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.success ? (
              <div className="space-y-4">
                {/* Quality Score */}
                {result.data.validation?.quality_score && (
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="font-medium">Quality Score</span>
                    <Badge variant="default">
                      {result.data.validation.quality_score.toFixed(1)}/100
                    </Badge>
                  </div>
                )}

                {/* Extracted Data Preview */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium mb-2">Vendor Information</h4>
                    <div className="space-y-1 text-sm">
                      <div><strong>Name:</strong> {result.data.result.vendor.name || 'N/A'}</div>
                      <div><strong>Tax ID:</strong> {result.data.result.vendor.tax_id || 'N/A'}</div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2">Financial Details</h4>
                    <div className="space-y-1 text-sm">
                      <div><strong>Total:</strong> {result.data.result.financial_details.total_amount} {result.data.result.financial_details.currency}</div>
                      <div><strong>Subtotal:</strong> {result.data.result.financial_details.subtotal || 'N/A'}</div>
                    </div>
                  </div>
                </div>

                {/* Validation Warnings */}
                {result.data.validation?.warnings?.length > 0 && (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center space-x-2 mb-2">
                      <AlertCircle className="h-4 w-4 text-yellow-600" />
                      <span className="font-medium text-yellow-800">Warnings</span>
                    </div>
                    <ul className="text-sm text-yellow-700 space-y-1">
                      {result.data.validation.warnings.map((warning: string, index: number) => (
                        <li key={index}>• {warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Full JSON (collapsed by default) */}
                <details className="border rounded-lg">
                  <summary className="p-3 cursor-pointer font-medium">
                    View Full JSON Response
                  </summary>
                  <div className="p-3 border-t bg-gray-50">
                    <pre className="text-xs overflow-auto">
                      {JSON.stringify(result.data, null, 2)}
                    </pre>
                  </div>
                </details>
              </div>
            ) : (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="font-medium text-red-800">Processing Failed</span>
                </div>
                <p className="text-sm text-red-700">{result.error}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}