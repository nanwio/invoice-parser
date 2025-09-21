'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, Heart, Sparkles } from 'lucide-react';
import { useUser } from '@/hooks/useUser';
import { PLANS } from '@/lib/plans';

export default function BillingPage() {
  const { dbUser } = useUser();
  const freePlan = PLANS.find(plan => plan.id === 'free');

  if (!freePlan) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Billing & Plan</h1>
        <p className="text-gray-600 mt-1">
          Manage your subscription and billing information.
        </p>
      </div>

      {/* Free Plan Notice */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
        <div className="flex items-center space-x-3 mb-3">
          <Heart className="h-6 w-6 text-red-500" />
          <h2 className="text-xl font-semibold text-gray-900">
            You're on our Free Plan!
          </h2>
        </div>
        <p className="text-gray-700 mb-4">
          Enjoy unlimited access to our invoice processing platform. We're committed to providing
          excellent service while we work on exciting premium features coming soon.
        </p>
        <div className="flex items-center space-x-2">
          <Sparkles className="h-4 w-4 text-yellow-500" />
          <span className="text-sm font-medium text-gray-600">
            Premium plans with advanced features launching Q1 2025
          </span>
        </div>
      </div>

      {/* Current Plan Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <span>Current Plan</span>
                <Badge variant="secondary">Active</Badge>
              </CardTitle>
              <CardDescription>
                Your current subscription and usage
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Plan Info */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <h3 className="font-semibold text-lg">{freePlan.name} Plan</h3>
                <p className="text-gray-600">{freePlan.description}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-green-600">€0</div>
                <div className="text-sm text-gray-500">Forever</div>
              </div>
            </div>

            {/* Features */}
            <div>
              <h4 className="font-medium mb-3">Included Features</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {freePlan.features.map((feature, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Limits */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <div className="text-sm font-medium text-gray-900">Monthly Processing</div>
                <div className="text-lg font-bold text-blue-600">
                  {freePlan.limits.monthly_processing} invoices
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-900">File Size Limit</div>
                <div className="text-lg font-bold text-blue-600">
                  {freePlan.limits.file_size_mb}MB
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Coming Soon */}
      <Card>
        <CardHeader>
          <CardTitle>🚀 Coming Soon</CardTitle>
          <CardDescription>
            We're working on exciting premium features
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle className="h-4 w-4" />
              <span>Unlimited processing</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle className="h-4 w-4" />
              <span>Advanced AI processing methods</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle className="h-4 w-4" />
              <span>Priority support</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle className="h-4 w-4" />
              <span>API integrations</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle className="h-4 w-4" />
              <span>Custom validation rules</span>
            </div>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              💡 <strong>Stay tuned!</strong> We'll notify you as soon as premium plans are available.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}