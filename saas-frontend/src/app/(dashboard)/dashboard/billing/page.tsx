'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle,
  CreditCard,
  Calendar,
  TrendingUp,
  AlertTriangle,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { useUser } from '@/hooks/useUser';
import { supabase } from '@/lib/supabase';
import { PLANS, getPlan } from '@/lib/plans';
import { Subscription } from '@/types';
import { toast } from 'sonner';

export default function BillingPage() {
  const { dbUser } = useUser();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const searchParams = useSearchParams();

  useEffect(() => {
    // Handle success/cancel from Stripe
    const success = searchParams.get('success');
    const canceled = searchParams.get('canceled');

    if (success) {
      toast.success('Subscription activated successfully!');
    } else if (canceled) {
      toast.error('Subscription setup was canceled.');
    }
  }, [searchParams]);

  useEffect(() => {
    async function loadSubscription() {
      if (!dbUser) return;

      try {
        setLoading(true);
        const { data, error } = await supabase
          .from('subscriptions')
          .select('*')
          .eq('user_id', dbUser.id)
          .single();

        if (error && error.code !== 'PGRST116') {
          throw error;
        }

        setSubscription(data);
      } catch (error) {
        console.error('Error loading subscription:', error);
      } finally {
        setLoading(false);
      }
    }

    loadSubscription();
  }, [dbUser]);

  const handleUpgrade = async (planId: string) => {
    const plan = getPlan(planId);
    if (!plan || !plan.stripe_price_id) return;

    setUpgrading(true);
    try {
      const response = await fetch('/api/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          priceId: plan.stripe_price_id,
          planType: plan.id,
        }),
      });

      const { url, error } = await response.json();

      if (error) {
        throw new Error(error);
      }

      window.location.href = url;
    } catch (error) {
      console.error('Error creating checkout session:', error);
      toast.error('Failed to start upgrade process');
    } finally {
      setUpgrading(false);
    }
  };

  const handleManageSubscription = async () => {
    try {
      const response = await fetch('/api/create-portal-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const { url, error } = await response.json();

      if (error) {
        throw new Error(error);
      }

      window.open(url, '_blank');
    } catch (error) {
      console.error('Error creating portal session:', error);
      toast.error('Failed to open billing portal');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-64 bg-gray-200 rounded animate-pulse"></div>
      </div>
    );
  }

  const currentPlan = getPlan(dbUser?.plan_type || 'free');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Billing & Subscription</h1>
        <p className="text-gray-600 mt-1">
          Manage your subscription and billing information.
        </p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <CreditCard className="h-5 w-5" />
            <span>Current Plan</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-2">
                <h3 className="text-2xl font-bold">{currentPlan?.name}</h3>
                <Badge variant={dbUser?.plan_type === 'free' ? 'secondary' : 'default'}>
                  {dbUser?.plan_type?.toUpperCase()}
                </Badge>
              </div>
              <p className="text-gray-600 mb-4">{currentPlan?.description}</p>

              {subscription && subscription.status === 'active' && (
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4" />
                    <span>
                      Next billing: {new Date(subscription.current_period_end!).toLocaleDateString()}
                    </span>
                  </div>
                  {subscription.cancel_at_period_end && (
                    <div className="flex items-center space-x-2 text-orange-600">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Subscription will cancel at period end</span>
                    </div>
                  )}
                </div>
              )}

              {subscription && subscription.status === 'past_due' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center space-x-2 text-red-800">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="font-medium">Payment Required</span>
                  </div>
                  <p className="text-sm text-red-700 mt-1">
                    Your subscription payment is past due. Please update your payment method.
                  </p>
                </div>
              )}
            </div>

            <div className="text-right">
              <div className="text-3xl font-bold">
                €{currentPlan?.price}
                {currentPlan?.price && currentPlan.price > 0 && (
                  <span className="text-lg font-normal text-gray-500">/{currentPlan.interval}</span>
                )}
              </div>
              {subscription && subscription.status === 'active' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleManageSubscription}
                  className="mt-2"
                >
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Manage
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plan Features */}
      <Card>
        <CardHeader>
          <CardTitle>Plan Features</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium mb-2">Processing Limits</h4>
              <div className="space-y-1 text-sm text-gray-600">
                <div>
                  Monthly: {currentPlan?.limits.monthly_processing === -1 ? 'Unlimited' : currentPlan?.limits.monthly_processing}
                </div>
                <div>
                  API calls: {currentPlan?.limits.api_calls === -1 ? 'Unlimited' : currentPlan?.limits.api_calls}
                </div>
                <div>File size: {currentPlan?.limits.file_size_mb}MB max</div>
              </div>
            </div>
            <div>
              <h4 className="font-medium mb-2">Available Methods</h4>
              <div className="space-y-1">
                {currentPlan?.limits.processing_methods.map((method) => (
                  <div key={method} className="flex items-center space-x-2 text-sm">
                    <CheckCircle className="h-3 w-3 text-green-600" />
                    <span className="capitalize">{method}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Available Plans */}
      {dbUser?.plan_type === 'free' && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Upgrade Your Plan</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {PLANS.filter(plan => plan.id !== 'free').map((plan) => (
              <Card
                key={plan.id}
                className={`relative ${
                  plan.id === 'pro'
                    ? 'border-2 border-blue-500 shadow-lg'
                    : 'border-2 hover:border-blue-200 transition-colors'
                }`}
              >
                {plan.id === 'pro' && (
                  <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-blue-600">
                    Most Popular
                  </Badge>
                )}

                <CardHeader className="text-center">
                  <CardTitle className="text-xl">{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                  <div className="mt-4">
                    <div className="text-3xl font-bold">€{plan.price}</div>
                    <div className="text-gray-500">/{plan.interval}</div>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="space-y-3 mb-6">
                    {plan.features.map((feature, index) => (
                      <div key={index} className="flex items-center space-x-2 text-sm">
                        <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>

                  <Button
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={upgrading}
                    className="w-full"
                    variant={plan.id === 'pro' ? 'default' : 'outline'}
                  >
                    {upgrading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <TrendingUp className="h-4 w-4 mr-2" />
                        Upgrade to {plan.name}
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}