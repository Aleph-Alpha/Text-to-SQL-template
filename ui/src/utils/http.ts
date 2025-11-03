import { type Http, http } from '@aleph-alpha/lib-http'
import type { CustomRagResponse, CustomRagRequest, QueryRequest, QueryResult, ErrorDetails } from '@/@core/models/api/customRag.ts'

export const HTTP_CLIENT = http({ timeout: 60_000 })

async function extractErrorDetails(error: any): Promise<ErrorDetails> {
  if (error.response && typeof error.response.json === 'function') {
    try {
      const responseData = await error.response.json()
      if (responseData.detail && typeof responseData.detail === 'object') {
        return responseData.detail as ErrorDetails
      }
    } catch (parseError) {
    }
  }
  
  if (error.data?.detail && typeof error.data.detail === 'object') {
    return error.data.detail as ErrorDetails
  }
  
  if (error instanceof Object && error.error_type && error.message && error.details) {
    return error as ErrorDetails
  }

  return {
    error_type: 'unknown_error',
    message: error.message || 'An unknown error occurred',
    details: 'Please try again or contact support if the issue persists.'
  }
}

export class CustomRagService {
  constructor(readonly httpClient: Http) {}

  async customQa(body: CustomRagRequest): Promise<CustomRagResponse> {
    try {
      return (await this.httpClient.post<CustomRagResponse>('qa', { body })).data
    } catch (error) {
      const errorDetails = await extractErrorDetails(error)
      const enhancedError = new Error(`QA request failed: ${errorDetails.message}`)
      ;(enhancedError as any).details = errorDetails
      throw enhancedError
    }
  }

  async executeQuery(body: QueryRequest): Promise<QueryResult> {
    try {
      return (await this.httpClient.post<QueryResult>('query', { body })).data
    } catch (error) {
      const errorDetails = await extractErrorDetails(error)
      const enhancedError = new Error(`Query execution failed: ${errorDetails.message}`)
      ;(enhancedError as any).details = errorDetails
      throw enhancedError
    }
  }

  async agentQuery(body: { message: string; context?: any }): Promise<CustomRagResponse> {
    try {
      // Call 1: Generate SQL
      const sqlResponse = await this.httpClient.post<any>('agent', { 
        body: { message: body.message, context: body.context }
      })
      
      const sqlData = sqlResponse.data
      
      if (sqlData.response_type === 'sql_query' && sqlData.success) {
        const sqlQuery = sqlData.data.sql_query
        
        // Call 2: Execute SQL automatically
        const execResponse = await this.httpClient.post<any>('agent', {
          body: { 
            message: `Execute this query: ${sqlQuery}`,
            context: { 
              query: sqlQuery,
              original_question: body.message
            }
          }
        })
        
        const execData = execResponse.data
        
        if (execData.response_type === 'query_results' && execData.success) {
          return {
            answer: sqlQuery,
            database_results: {
              queries_found: true,
              results: [execData.data]
            }
          }
        }
        
        // If execution failed, return just SQL
        return { answer: sqlQuery }
      }
      
      // If SQL generation failed
      throw new Error(sqlData.data.error || 'Failed to generate SQL')
      
    } catch (error) {
      const errorDetails = await extractErrorDetails(error)
      const enhancedError = new Error(`Agent query failed: ${errorDetails.message}`)
      ;(enhancedError as any).details = errorDetails
      throw enhancedError
    }
  }
}

export const CUSTOM_RAG_SERVICE = new CustomRagService(HTTP_CLIENT)
