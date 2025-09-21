'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Upload,
  FileText,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  ArrowRight,
  BarChart3,
} from 'lucide-react';
import { useUser } from '@/hooks/useUser';
import { supabase } from '@/lib/supabase';
import { getUserPlanLimits } from '@/lib/plans';

interface DashboardStats {
  totalProcessed: number;
  successfulProcessed: number;
  currentMonthUsage: number;
  averageProcessingTime: number;
  recentProcessing: any[];
}

export default function DashboardPage() {
  const { dbUser, loading } = useUser();
  const [stats, setStats] = useState<DashboardStats>({
    totalProcessed: 0,
    successfulProcessed: 0,
    currentMonthUsage: 0,
    averageProcessingTime: 0,
    recentProcessing: [],
  });
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    async function loadStats() {
      if (!dbUser) return;

      try {
        setLoadingStats(true);

        // Get current month usage
        const currentMonth = new Date().toISOString().slice(0, 7) + '-01';
        const { data: monthlyUsage } = await supabase
          .from('usage_tracking')
          .select('*')
          .eq('user_id', dbUser.id)
          .eq('month', currentMonth)
          .single();

        // Get total stats
        const { data: totalStats } = await supabase
          .from('invoice_processing')
          .select('processing_time_seconds, success')
          .eq('user_id', dbUser.id);

        // Get recent processing
        const { data: recentProcessing } = await supabase
          .from('invoice_processing')
          .select('*')
          .eq('user_id', dbUser.id)
          .order('created_at', { ascending: false })
          .limit(5);

        const totalProcessed = totalStats?.length || 0;
        const successfulProcessed = totalStats?.filter(item => item.success).length || 0;
        const averageTime = totalStats?.reduce((acc, item) => acc + (item.processing_time_seconds || 0), 0) / totalProcessed || 0;

        setStats({
          totalProcessed,
          successfulProcessed,
          currentMonthUsage: monthlyUsage?.total_processed || 0,
          averageProcessingTime: averageTime,
          recentProcessing: recentProcessing || [],
        });
      } catch (error) {
        console.error('Error loading stats:', error);
      } finally {
        setLoadingStats(false);
      }
    }

    loadStats();
  }, [dbUser]);

  if (loading || loadingStats) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  const planLimits = getUserPlanLimits(dbUser?.plan_type || 'free');
  const usagePercentage = planLimits.monthly_processing === -1
    ? 0
    : Math.round((stats.currentMonthUsage / planLimits.monthly_processing) * 100);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Welcome back! Here's your invoice processing overview.
          </p>
        </div>
        <Link href="/dashboard/upload">
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Upload Invoice
          </Button>
        </Link>
      </div>

      {/* Usage Alert */}
      {usagePercentage > 80 && planLimits.monthly_processing !== -1 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-orange-800">Usage Warning</h3>
              <p className="text-sm text-orange-700 mt-1">
                You've used {usagePercentage}% of your monthly processing limit.
              </p>
            </div>
            <Link href="/dashboard/billing">
              <Button size="sm" variant="outline">
                Upgrade Plan
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Usage</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.currentMonthUsage}
              {planLimits.monthly_processing !== -1 && (
                <span className="text-sm font-normal text-gray-500">
                  /{planLimits.monthly_processing}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {planLimits.monthly_processing === -1 ? 'Unlimited' : `${usagePercentage}% used`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Processed</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalProcessed}</div>
            <p className="text-xs text-muted-foreground">
              All time invoices
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.totalProcessed > 0
                ? Math.round((stats.successfulProcessed / stats.totalProcessed) * 100)
                : 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.successfulProcessed}/{stats.totalProcessed} successful
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.averageProcessingTime.toFixed(1)}s
            </div>
            <p className="text-xs text-muted-foreground">
              Average processing time
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Processing</CardTitle>
            <CardDescription>
              Your latest invoice processing activity
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats.recentProcessing.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No invoices processed yet</p>
                <Link href="/dashboard/upload">
                  <Button className="mt-4">
                    Upload Your First Invoice
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {stats.recentProcessing.map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {item.success ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                      <div>
                        <p className="font-medium text-sm">{item.file_name}</p>
                        <p className="text-xs text-gray-500">
                          {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={item.success ? 'default' : 'destructive'}>
                        {item.processing_method}
                      </Badge>
                      <p className="text-xs text-gray-500 mt-1">
                        {item.processing_time_seconds?.toFixed(1)}s
                      </p>
                    </div>
                  </div>
                ))}
                <Link href="/dashboard/history">
                  <Button variant="outline" className="w-full">
                    View All History
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Get started with these common tasks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link href="/dashboard/upload">
              <Button className="w-full justify-start">
                <Upload className="h-4 w-4 mr-2" />
                Upload New Invoice
              </Button>
            </Link>
            <Link href="/dashboard/history">
              <Button variant="outline" className="w-full justify-start">
                <FileText className="h-4 w-4 mr-2" />
                View Processing History
              </Button>
            </Link>
            {dbUser?.plan_type === 'free' && (
              <Link href="/dashboard/billing">
                <Button variant="outline" className="w-full justify-start">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Upgrade Plan
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}