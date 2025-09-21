'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  CheckCircle,
  XCircle,
  Clock,
  Download,
  Search,
  Filter,
  FileText,
  Calendar,
} from 'lucide-react';
import { useUser } from '@/hooks/useUser';
import { supabase } from '@/lib/supabase';
import { InvoiceProcessing } from '@/types';

export default function HistoryPage() {
  const { dbUser } = useUser();
  const [processing, setProcessing] = useState<InvoiceProcessing[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [methodFilter, setMethodFilter] = useState<string>('all');

  useEffect(() => {
    async function loadHistory() {
      if (!dbUser) return;

      try {
        setLoading(true);
        const { data, error } = await supabase
          .from('invoice_processing')
          .select('*')
          .eq('user_id', dbUser.id)
          .order('created_at', { ascending: false });

        if (error) throw error;
        setProcessing(data || []);
      } catch (error) {
        console.error('Error loading processing history:', error);
      } finally {
        setLoading(false);
      }
    }

    loadHistory();
  }, [dbUser]);

  const filteredProcessing = processing.filter((item) => {
    const matchesSearch = item.file_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'success' && item.success) ||
      (statusFilter === 'failed' && !item.success);
    const matchesMethod = methodFilter === 'all' || item.processing_method === methodFilter;

    return matchesSearch && matchesStatus && matchesMethod;
  });

  const downloadResults = (item: InvoiceProcessing) => {
    const dataStr = JSON.stringify(item.result_json, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

    const exportFileDefaultName = `${item.file_name.replace('.pdf', '')}_results.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-64 bg-gray-200 rounded animate-pulse"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Processing History</h1>
        <p className="text-gray-600 mt-1">
          View and manage your invoice processing history.
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search by filename..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="success">Successful</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Method</label>
              <Select value={methodFilter} onValueChange={setMethodFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Methods</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="enhanced">Enhanced</SelectItem>
                  <SelectItem value="fast">Fast</SelectItem>
                  <SelectItem value="lightning">Lightning</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>Processing History</CardTitle>
          <CardDescription>
            {filteredProcessing.length} of {processing.length} records
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredProcessing.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 mb-2">
                {processing.length === 0 ? 'No processing history yet' : 'No results match your filters'}
              </p>
              <p className="text-sm text-gray-400">
                {processing.length === 0 ? 'Upload your first invoice to get started' : 'Try adjusting your filters'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredProcessing.map((item) => (
                <div
                  key={item.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        {item.success ? (
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600" />
                        )}
                        <div>
                          <p className="font-medium">{item.file_name}</p>
                          <div className="flex items-center space-x-2 text-sm text-gray-500">
                            <Calendar className="h-3 w-3" />
                            <span>{new Date(item.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <Badge
                          variant={item.success ? 'default' : 'destructive'}
                          className="mb-1"
                        >
                          {item.processing_method}
                        </Badge>
                        <div className="flex items-center space-x-1 text-xs text-gray-500">
                          <Clock className="h-3 w-3" />
                          <span>{item.processing_time_seconds?.toFixed(2)}s</span>
                        </div>
                      </div>

                      {item.quality_score && (
                        <div className="text-center">
                          <div className="text-sm font-medium">Quality</div>
                          <Badge variant="outline">
                            {item.quality_score.toFixed(0)}/100
                          </Badge>
                        </div>
                      )}

                      {item.success && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => downloadResults(item)}
                        >
                          <Download className="h-4 w-4 mr-1" />
                          Download
                        </Button>
                      )}
                    </div>
                  </div>

                  {!item.success && item.error_message && (
                    <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                      <strong>Error:</strong> {item.error_message}
                    </div>
                  )}

                  {item.success && item.result_json && (
                    <div className="mt-3">
                      <details className="group">
                        <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900">
                          View Processing Results
                        </summary>
                        <div className="mt-2 p-3 bg-gray-50 rounded border text-xs">
                          {/* Quick preview of key data */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                            {item.result_json?.result?.vendor?.name && (
                              <div>
                                <strong>Vendor:</strong> {item.result_json.result.vendor.name}
                              </div>
                            )}
                            {item.result_json?.result?.financial_details?.total_amount && (
                              <div>
                                <strong>Total:</strong> {item.result_json.result.financial_details.total_amount} {item.result_json.result.financial_details.currency}
                              </div>
                            )}
                            {item.result_json?.result?.metadata?.invoice_number && (
                              <div>
                                <strong>Invoice #:</strong> {item.result_json.result.metadata.invoice_number}
                              </div>
                            )}
                          </div>

                          <details>
                            <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                              View Full JSON
                            </summary>
                            <pre className="mt-2 overflow-auto max-h-40">
                              {JSON.stringify(item.result_json, null, 2)}
                            </pre>
                          </details>
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}