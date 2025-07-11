import { Container } from "@cloudflare/containers"

// Define the container configuration
export class InvoiceParsingContainer extends Container {
  defaultPort = 8000
  
  // Keep container alive for 30 minutes after last request
  sleepAfter = "30m"
  
  // Override the constructor to set environment variables
  constructor(state: DurableObjectState, env: Env) {
    super(state, env)
    
    // Pass environment variables from Worker to Container
    this.envVars = {
      ENVIRONMENT: env.ENVIRONMENT,
      MAX_FILE_SIZE_MB: env.MAX_FILE_SIZE_MB,
      CACHE_ENABLED: env.CACHE_ENABLED,

      // Secrets
      SECRET_KEY: env.SECRET_KEY,
      GEMINI_API_KEY: env.GEMINI_API_KEY,
      GEMINI_MODEL_NAME: env.GEMINI_MODEL_NAME || "gemini-2.5-flash-lite-preview-06-17",
      
      // Redis/Cache Configuration
      REDIS_URL: env.REDIS_URL || "",
      CACHE_TTL: env.CACHE_TTL || "86400",
      
      // Performance
      REQUEST_TIMEOUT: env.REQUEST_TIMEOUT || "120",
      
      // KV cache strategy credentials
      CF_ACCOUNT_ID: env.CF_ACCOUNT_ID || "",
      CF_API_TOKEN: env.CF_API_TOKEN || "",
      KV_NAMESPACE_ID: env.KV_NAMESPACE_ID || "",
    }
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      // Get or create a container instance
      // Using a fixed ID means all requests go to the same container instance
      const containerId = env.INVOICE_PARSING.idFromName("main-instance")
      const container = env.INVOICE_PARSING.get(containerId)
      
      // Forward the request to the container
      // and it will handle all routing internally
      return await container.fetch(request)
    } catch (error) {
      console.error("Error routing request to container:", error)
      return new Response("Internal Server Error", { status: 500 })
    }
  },
}

// TypeScript types for environment bindings
interface Env {
  // Container binding
  INVOICE_PARSING: DurableObjectNamespace
  
  // Environment variables (from wrangler.jsonc vars)
  ENVIRONMENT: string
  MAX_FILE_SIZE_MB: string
  CACHE_ENABLED: string
  
  // Secrets (from .env)
  SECRET_KEY: string
  GEMINI_API_KEY: string
  GEMINI_MODEL_NAME?: string
  REDIS_URL?: string
  CACHE_TTL?: string
  REQUEST_TIMEOUT?: string
  CF_ACCOUNT_ID?: string
  CF_API_TOKEN?: string
  KV_NAMESPACE_ID?: string
}