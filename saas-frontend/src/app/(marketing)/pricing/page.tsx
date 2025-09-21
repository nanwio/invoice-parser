import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Brain, ArrowRight } from "lucide-react";
import { PLANS } from "@/lib/plans";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <Brain className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-gray-900">InvoiceAI</span>
          </Link>
          <nav className="hidden md:flex items-center space-x-6">
            <Link href="/features" className="text-gray-600 hover:text-gray-900">
              Features
            </Link>
            <Link href="/pricing" className="text-gray-600 hover:text-gray-900">
              Pricing
            </Link>
            <Link href="/sign-in">
              <Button variant="outline">Sign In</Button>
            </Link>
            <Link href="/sign-up">
              <Button>Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center max-w-4xl">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Simple, Transparent{" "}
            <span className="text-blue-600">Pricing</span>
          </h1>
          <p className="text-xl text-gray-600 mb-12 leading-relaxed">
            Choose the perfect plan for your business. Start free, upgrade as you grow.
            No hidden fees, cancel anytime.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-20 px-4">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {PLANS.map((plan, index) => (
              <Card
                key={plan.id}
                className={`relative ${
                  plan.id === 'pro'
                    ? 'border-2 border-blue-500 shadow-xl scale-105'
                    : 'border-2 hover:border-blue-200 transition-colors'
                }`}
              >
                {plan.id === 'pro' && (
                  <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-blue-600">
                    Most Popular
                  </Badge>
                )}

                <CardHeader className="text-center pb-8">
                  <CardTitle className="text-2xl font-bold">{plan.name}</CardTitle>
                  <CardDescription className="text-gray-600 mt-2">
                    {plan.description}
                  </CardDescription>
                  <div className="mt-6">
                    <div className="flex items-center justify-center">
                      <span className="text-4xl font-bold text-gray-900">
                        €{plan.price}
                      </span>
                      {plan.price > 0 && (
                        <span className="text-gray-600 ml-2">/{plan.interval}</span>
                      )}
                    </div>
                    {plan.price === 0 && (
                      <p className="text-sm text-gray-500 mt-1">Forever free</p>
                    )}
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="space-y-4 mb-8">
                    {plan.features.map((feature, featureIndex) => (
                      <div key={featureIndex} className="flex items-start space-x-3">
                        <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-700">{feature}</span>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-3 mb-8 p-4 bg-gray-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-900">Plan Limits:</div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                      <div>Monthly: {plan.limits.monthly_processing === -1 ? 'Unlimited' : plan.limits.monthly_processing}</div>
                      <div>API calls: {plan.limits.api_calls === -1 ? 'Unlimited' : plan.limits.api_calls}</div>
                      <div>File size: {plan.limits.file_size_mb}MB</div>
                      <div>Methods: {plan.limits.processing_methods.length}</div>
                    </div>
                  </div>

                  <Link href="/sign-up" className="block">
                    <Button
                      className={`w-full ${
                        plan.id === 'pro'
                          ? 'bg-blue-600 hover:bg-blue-700'
                          : ''
                      }`}
                      variant={plan.id === 'pro' ? 'default' : 'outline'}
                    >
                      {plan.price === 0 ? 'Start Free' : 'Get Started'}
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Everything you need to know about our plans and pricing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Can I change plans at any time?
              </h3>
              <p className="text-gray-600">
                Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately and we'll prorate the billing.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Is there a free trial?
              </h3>
              <p className="text-gray-600">
                Our Free plan includes 10 invoices per month forever. For paid plans, we offer a 14-day free trial with full access.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What file formats do you support?
              </h3>
              <p className="text-gray-600">
                Currently we support PDF files up to the size limit of your plan. We're working on adding support for images and other formats.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Do you offer custom enterprise solutions?
              </h3>
              <p className="text-gray-600">
                Yes! Contact our sales team for custom integrations, higher volume processing, and dedicated support options.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-blue-600">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Join thousands of businesses using InvoiceAI to automate their invoice processing.
            Start your free trial today.
          </p>
          <Link href="/sign-up">
            <Button size="lg" variant="secondary" className="text-lg px-8">
              Start Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Brain className="h-6 w-6 text-blue-400" />
                <span className="text-xl font-bold">InvoiceAI</span>
              </div>
              <p className="text-gray-400">
                AI-powered invoice processing for modern businesses.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <div className="space-y-2 text-gray-400">
                <Link href="/features" className="block hover:text-white">Features</Link>
                <Link href="/pricing" className="block hover:text-white">Pricing</Link>
                <div>API Documentation</div>
              </div>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <div className="space-y-2 text-gray-400">
                <div>About</div>
                <div>Blog</div>
                <div>Contact</div>
              </div>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <div className="space-y-2 text-gray-400">
                <div>Help Center</div>
                <div>Status</div>
                <div>Privacy Policy</div>
              </div>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2025 Artificial Intelligence Labs, SL. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}