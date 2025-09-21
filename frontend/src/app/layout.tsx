import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClerkProvider } from '@clerk/nextjs';
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InvoiceAI SaaS - AI-Powered Invoice Processing",
  description: "Transform your invoice processing with AI. Extract structured data from PDFs with professional validation and quality scoring.",
  keywords: ["invoice processing", "AI", "OCR", "document automation", "SaaS"],
  authors: [{ name: "Artificial Intelligence Labs, SL" }],
  openGraph: {
    title: "InvoiceAI SaaS - AI-Powered Invoice Processing",
    description: "Transform your invoice processing with AI. Extract structured data from PDFs with professional validation and quality scoring.",
    type: "website",
    url: "https://invoiceai.ai-labs.es",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={`${inter.className} antialiased`}>
          {children}
          <Toaster />
        </body>
      </html>
    </ClerkProvider>
  );
}
