import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Zap,
  Shield,
  BarChart3,
  Clock,
  CheckCircle,
  ArrowRight,
  FileText,
  Brain,
  Sparkles,
  Target
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-gray-900">InvoiceAI</span>
          </div>
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
          <Badge className="mb-4" variant="secondary">
            <Sparkles className="h-4 w-4 mr-1" />
            AI-Powered Invoice Processing
          </Badge>
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Transform Your Invoice Processing with{" "}
            <span className="text-blue-600">AI</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            Extract structured data from PDF invoices in seconds. Professional validation,
            quality scoring, and multiple processing strategies for every business need.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Link href="/sign-up">
              <Button size="lg" className="text-lg px-8">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/features">
              <Button size="lg" variant="outline" className="text-lg px-8">
                View Demo
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2">99.2%</div>
              <div className="text-gray-600">Accuracy Rate</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2">&lt;3s</div>
              <div className="text-gray-600">Processing Time</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2">10k+</div>
              <div className="text-gray-600">Invoices Processed</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Multiple Processing Strategies
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Choose the perfect processing method for your specific needs - from lightning-fast
              extraction to professional-grade validation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="border-2 hover:border-blue-200 transition-colors">
              <CardHeader>
                <FileText className="h-10 w-10 text-blue-600 mb-2" />
                <CardTitle>Standard</CardTitle>
                <CardDescription>Reliable processing with caching</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-gray-600">
                  <div>• 2-5 seconds</div>
                  <div>• Document classification</div>
                  <div>• Smart caching</div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 hover:border-blue-200 transition-colors">
              <CardHeader>
                <Shield className="h-10 w-10 text-green-600 mb-2" />
                <CardTitle>Enhanced</CardTitle>
                <CardDescription>Professional validation</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-gray-600">
                  <div>• 3-8 seconds</div>
                  <div>• Image preprocessing</div>
                  <div>• Quality scoring</div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 hover:border-blue-200 transition-colors">
              <CardHeader>
                <Zap className="h-10 w-10 text-orange-600 mb-2" />
                <CardTitle>Fast</CardTitle>
                <CardDescription>DONUT OCR + Gemini fallback</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-gray-600">
                  <div>• &lt;5 seconds</div>
                  <div>• Hybrid processing</div>
                  <div>• Performance metrics</div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 hover:border-blue-200 transition-colors">
              <CardHeader>
                <Target className="h-10 w-10 text-purple-600 mb-2" />
                <CardTitle>Lightning</CardTitle>
                <CardDescription>Maximum speed optimization</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-gray-600">
                  <div>• &lt;3 seconds</div>
                  <div>• Pre-loaded models</div>
                  <div>• Cache-first approach</div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-4xl font-bold text-gray-900 mb-6">
                Why Choose InvoiceAI?
              </h2>
              <div className="space-y-6">
                <div className="flex items-start space-x-4">
                  <CheckCircle className="h-6 w-6 text-green-600 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Professional Validation</h3>
                    <p className="text-gray-600">Mathematical consistency checks, Spanish tax ID validation, and quality scoring for business confidence.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <CheckCircle className="h-6 w-6 text-green-600 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Enterprise-Grade Performance</h3>
                    <p className="text-gray-600">Multi-tier caching, model pre-loading, and optimized processing for high-volume requirements.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <CheckCircle className="h-6 w-6 text-green-600 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Scalable Architecture</h3>
                    <p className="text-gray-600">Built for production with FastAPI, Redis caching, and cloud-native deployment ready.</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-purple-50 p-8 rounded-2xl">
              <div className="grid grid-cols-2 gap-6">
                <div className="text-center">
                  <Clock className="h-10 w-10 text-blue-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-gray-900">10x</div>
                  <div className="text-gray-600">Faster Processing</div>
                </div>
                <div className="text-center">
                  <BarChart3 className="h-10 w-10 text-green-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-gray-900">99%</div>
                  <div className="text-gray-600">Accuracy Rate</div>
                </div>
                <div className="text-center">
                  <Shield className="h-10 w-10 text-purple-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-gray-900">SOC2</div>
                  <div className="text-gray-600">Compliant</div>
                </div>
                <div className="text-center">
                  <Zap className="h-10 w-10 text-orange-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-gray-900">24/7</div>
                  <div className="text-gray-600">Uptime</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-blue-600">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to Transform Your Invoice Processing?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Join thousands of businesses using InvoiceAI to automate their document processing.
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
                <div>Features</div>
                <div>Pricing</div>
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