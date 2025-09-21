import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Get started</h1>
          <p className="text-gray-600 mt-2">Create your InvoiceAI account</p>
        </div>
        <SignUp />
      </div>
    </div>
  );
}