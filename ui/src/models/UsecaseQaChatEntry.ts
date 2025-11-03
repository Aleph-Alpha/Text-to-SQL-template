export enum UsecaseQaAnswerStatus {
  PENDING = 'pending',
  FAILED = 'failed',
  SUCCESSFUL = 'successful',
}

export type DatabaseResults = {
  queries_found: boolean
  results: any[]
}

export type ErrorDetails = {
  error_type: string
  message: string
  details: string
}

export type UsecaseQaAnswer = {
  traceId?: string
  answer?: string
  status: UsecaseQaAnswerStatus
  database_results?: DatabaseResults
  error?: ErrorDetails
}

export interface BaseQaChatEntry {
  questionId: string
  question: string
  timestamp: Date
}

export interface UsecaseQaDocumentChatEntry extends BaseQaChatEntry {
  answer: UsecaseQaAnswer
}

export interface UsecaseQaDocumentIndexChatEntry extends BaseQaChatEntry {
  namespace: string
  collection: string
  answer: UsecaseQaAnswer
}

export type UsecaseQaChatEntry = UsecaseQaDocumentChatEntry | UsecaseQaDocumentIndexChatEntry

export type UsecaseQaChatInitializationEntry =
  | Omit<UsecaseQaDocumentChatEntry, 'questionId' | 'timestamp' | 'answer'>
  | Omit<UsecaseQaDocumentIndexChatEntry, 'questionId' | 'timestamp' | 'answer'>
