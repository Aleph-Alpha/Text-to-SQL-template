<script lang="ts" setup>
import UsecaseQaAnswerActions from './UsecaseQaAnswerActions.vue'
import SkeletonPlaceholderContainer from '@/@core/components/SkeletonPlaceholderContainer.vue'
import DatabaseResultTable from './DatabaseResultTable.vue'
import SqlDisplay from './SqlDisplay.vue'
import { UsecaseQaAnswerStatus, type UsecaseQaChatEntry } from '@/models/UsecaseQaChatEntry'
import { AaText } from '@aleph-alpha/ds-components-vue'
import { computed } from 'vue'
import { extractSQLFromText } from '@/utils/sqlFormatter'

const props = defineProps<{
  chatEntry: UsecaseQaChatEntry
}>()


const isExecutingQueries = computed(() => {
  return props.chatEntry.answer.status === UsecaseQaAnswerStatus.SUCCESSFUL && 
         props.chatEntry.answer.answer && 
         !props.chatEntry.answer.database_results &&
         extractSQLFromText(props.chatEntry.answer.answer)
})

const extractedSQL = computed(() => {
  if (!props.chatEntry.answer.answer) return null
  return extractSQLFromText(props.chatEntry.answer.answer)
})

const answerWithoutSQL = computed(() => {
  if (!props.chatEntry.answer.answer) return 'No answer found'
  
  const sql = extractedSQL.value
  if (!sql) return props.chatEntry.answer.answer
  
  let cleanAnswer = props.chatEntry.answer.answer
  
  cleanAnswer = cleanAnswer.replace(/```(?:sql)?\s*(.*?)\s*```/gis, '')
  
  cleanAnswer = cleanAnswer.replace(/(SELECT\s+(?:(?!SELECT\s+)[\s\S])*?(?:;|$))/gi, '')
  
  return cleanAnswer.trim()
})

</script>

<template>
  <div class="w-179 p-M gap-XS text-core-content-primary flex grow rounded">
    <div
      class="border-core-border-default flex size-8 flex-shrink-0 items-center justify-center rounded-full border"
    >
      <span class="i-aa-logo flex size-4 flex-shrink-0" />
    </div>
    <SkeletonPlaceholderContainer
      v-if="chatEntry.answer.status === UsecaseQaAnswerStatus.PENDING"
      :bar-count="4"
      :bar-height-px="32"
      class="gap-y-lg"
    />
    <div v-else-if="chatEntry.answer.status === UsecaseQaAnswerStatus.FAILED" class="flex w-full flex-col justify-center">
      <div class="mb-2">
        <AaText element="h4" class="text-sm font-medium text-core-content-secondary mb-2">
          Error Occurred:
        </AaText>
        
        <div v-if="chatEntry.answer.error" 
             :class="`p-4 rounded border bg-red-50 border-red-200 text-red-600`">
          <div class="flex items-start space-x-3">
            <span class="flex-shrink-0 w-5 h-5 i-aa-alert-triangle"></span>
            <div class="flex-1">
              <div class="font-medium text-sm mb-1">
                {{ chatEntry.answer.error.message }}
              </div>
              <div class="text-sm opacity-80">
                {{ chatEntry.answer.error.details }}
              </div>
              <div class="text-xs mt-2 opacity-60">
                Error Type: {{ chatEntry.answer.error.error_type }}
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="p-4 rounded border bg-red-50 border-red-200 text-red-600">
          <div class="flex items-start space-x-3">
            <span class="flex-shrink-0 w-5 h-5 i-aa-alert-triangle"></span>
            <div class="flex-1">
              <div class="font-medium text-sm mb-1">
                Request Failed
              </div>
              <div class="text-sm opacity-80">
                Something went wrong while processing your request. Please try again.
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="pt-L text-core-content-tertiary flex items-center justify-between">
        <UsecaseQaAnswerActions :chat-entry="chatEntry" />
      </div>
    </div>
    <div v-else class="flex w-full flex-col justify-center">
      <div v-if="extractedSQL" class="mb-2">
        <SqlDisplay 
          :sql="extractedSQL" 
          title="Generated SQL" 
          :show-copy="true"
        />
      </div>
      
      <div v-if="isExecutingQueries" class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
        <div class="flex items-center space-x-2">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <AaText element="span" class="text-blue-700 text-sm">
            Executing SQL queries automatically...
          </AaText>
        </div>
      </div>
      
      <div v-if="chatEntry.answer.database_results?.queries_found" class="mt-4">
        <DatabaseResultTable 
          v-for="(result, index) in chatEntry.answer.database_results.results" 
          :key="index"
          :result="result"
        />
      </div>
    </div>
  </div>
</template>
