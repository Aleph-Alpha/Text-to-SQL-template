import { z } from 'zod'

export interface CustomRagRequest {
  question: string
}

export interface QueryRequest {
  query: string
}

export interface ErrorDetails {
  error_type: string
  message: string
  details: string
}

export interface QueryResult {
  query: string
  headers: string[]
  rows: any[][]
  count: number
  error?: ErrorDetails
}

export const CUSTOM_RAG_RESPONSE_SCHEMA = z.object({
  answer: z.string().optional(),
  database_results: z.object({
    queries_found: z.boolean(),
    results: z.array(z.any())
  }).optional(),
})

export type CustomRagResponse = z.infer<typeof CUSTOM_RAG_RESPONSE_SCHEMA>
