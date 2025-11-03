import { useUsecaseQaChatStore } from '@/stores/usecaseQaChat'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { CUSTOM_RAG_SERVICE } from '@/utils/http.ts'
import type { QueryResult, ErrorDetails } from '@/@core/models/api/customRag'

export const useUsecaseQaStore = defineStore('usecase-qa', () => {
  const usecaseChatStore = useUsecaseQaChatStore()
  const isProcessingRequest = ref<{ [key: string]: boolean }>({})

  function extractErrorDetails(error: any): ErrorDetails {
    if (error.details && typeof error.details === 'object') {
      return error.details
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

  async function executeUsecase(usecaseId: string, question: string) {
    isProcessingRequest.value[usecaseId] = true

    const questionId = usecaseChatStore.createEntry(usecaseId, {
      question,
    })

    try {
      // Use new agent approach - it makes 2 calls internally
      const response = await CUSTOM_RAG_SERVICE.agentQuery({ 
        message: question
      })
      
      const databaseResults = response.database_results
      
      usecaseChatStore.addAnswer(usecaseId, questionId, {
        traceId: '',
        answer: response.answer,
        database_results: databaseResults
      })
      
      isProcessingRequest.value[usecaseId] = false
    } catch (error) {
      const errorDetails = extractErrorDetails(error)
      usecaseChatStore.flagEntryAsFailed(usecaseId, questionId, errorDetails)
      isProcessingRequest.value[usecaseId] = false

      throw error
    }
  }

  const submitQuestion = async (usecaseId: string, question: string) => {
    if (!question) return
    await executeUsecase(usecaseId, question)
  }

  return {
    isProcessingRequest,
    submitQuestion,
  }
})
