<script lang="ts" setup>
import type { QueryResult, ErrorDetails } from '@/@core/models/api/customRag'
import { AaText, AaButton } from '@aleph-alpha/ds-components-vue'
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { HTTP_CLIENT } from '@/utils/http.ts'

const props = defineProps<{
  result: QueryResult
}>()

const viewMode = ref<'table' | 'chart'>('table')
const chartImageUrl = ref<string | null>(null)
const isLoadingChart = ref(false)
const chartError = ref<string | null>(null)
const chartReady = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const canGenerateChart = computed(() => {
  return props.result.count > 0 && props.result.headers.length >= 1
})

const isChartButtonDisabled = computed(() => {
  return !canGenerateChart.value || (isLoadingChart.value && !chartReady.value)
})

function isDetailedError(error: string | ErrorDetails | undefined): error is ErrorDetails {
  return typeof error === 'object' && error !== null && 'error_type' in error
}

async function generateChart() {
  if (!canGenerateChart.value || isLoadingChart.value) return
  
  isLoadingChart.value = true
  chartError.value = null
  chartReady.value = false
  
  try {
    // Call agent with context containing query data
    const response = await HTTP_CLIENT.post('agent', {
      body: {
        message: 'Create visualization',
        context: {
          query: props.result.query || '',
          headers: props.result.headers,
          rows: props.result.rows
        }
      }
    })
    
    const agentData = response.data as any
    
    // Check response type
    if (agentData.response_type === 'chart_image' && agentData.success) {
      const base64Image = agentData.data.chart_image as string
      
      // Decode base64 to blob
      const binaryString = atob(base64Image)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      const blob = new Blob([bytes], { type: 'image/png' })
      
      if (blob && blob.size > 0) {
        chartImageUrl.value = URL.createObjectURL(blob)
        chartReady.value = true
      } else {
        throw new Error('Received empty image data')
      }
    } else {
      throw new Error(agentData.data?.error || 'Failed to generate chart')
    }
  } catch (error) {
    chartError.value = `Failed to generate chart: ${error instanceof Error ? error.message : String(error)}`
    chartReady.value = false
  } finally {
    isLoadingChart.value = false
  }
}

async function toggleView(mode: 'table' | 'chart') {
  // Store current scroll position relative to the container
  const scrollY = window.scrollY
  const containerTop = containerRef.value?.getBoundingClientRect().top ?? 0
  const absoluteTop = scrollY + containerTop
  
  if (mode === 'chart' && chartReady.value && chartImageUrl.value) {
    viewMode.value = 'chart'
  } else if (mode === 'table') {
    viewMode.value = 'table'
  }
  
  // Wait for DOM to update, then restore scroll position
  await nextTick()
  
  // Smooth scroll to keep this component in view
  if (containerRef.value) {
    const newTop = containerRef.value.getBoundingClientRect().top + window.scrollY
    const offset = 100 // Offset from top for better visibility
    window.scrollTo({
      top: newTop - offset,
      behavior: 'smooth'
    })
  }
}

// Auto-generate chart when data is available
function autoGenerateChart() {
  if (canGenerateChart.value && !chartImageUrl.value && !isLoadingChart.value) {
    generateChart()
  }
}

// Auto-generate chart when component mounts or data changes
onMounted(() => {
  autoGenerateChart()
})

// Watch for changes in the result data and auto-generate chart
watch(() => props.result, () => {
  // Reset chart state when new data comes in
  chartImageUrl.value = null
  chartReady.value = false
  chartError.value = null
  
  // Auto-generate chart for new data
  setTimeout(() => {
    autoGenerateChart()
  }, 100) // Small delay to ensure DOM is updated
}, { deep: true })
</script>

<template>
  <div ref="containerRef" class="w-full mt-4" style="scroll-margin-top: 100px;">

    <div v-if="result.error" class="mb-2">
      <div v-if="isDetailedError(result.error)" 
           class="p-3 rounded border bg-red-50 border-red-200 text-red-600">
        <div class="flex items-start space-x-2">
          <span class="flex-shrink-0 w-4 h-4 i-aa-alert-triangle"></span>
          <div class="flex-1">
            <div class="font-medium text-sm mb-1">
              {{ result.error.message }}
            </div>
            <div class="text-xs opacity-80">
              {{ result.error.details }}
            </div>
            <div class="text-xs mt-1 opacity-60">
              Error Type: {{ result.error.error_type }}
            </div>
          </div>
        </div>
      </div>
      
      <div v-else class="p-3 bg-red-50 border border-red-200 rounded text-red-600">
        <div class="flex items-start space-x-2">
          <span class="flex-shrink-0 w-4 h-4 i-aa-alert-triangle"></span>
          <div class="flex-1">
            <AaText element="p" class="text-sm">
              <strong>Error:</strong> {{ result.error }}
            </AaText>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else>
        <div class="mb-4 flex items-center justify-between">
        <AaText element="span" class="text-sm text-core-content-secondary">
          Results: {{ result.count }} row(s)
        </AaText>
        
        <!-- View Toggle Buttons -->
        <div v-if="canGenerateChart" class="flex gap-2">
          <AaButton
            :variant="viewMode === 'table' ? 'primary' : 'secondary'"
            size="small"
            @click="toggleView('table')"
          >
            <span class="i-aa-table mr-1"></span>Table
          </AaButton>
          <AaButton
            :variant="viewMode === 'chart' ? 'primary' : 'secondary'"
            size="small"
            :disabled="isChartButtonDisabled"
            @click="toggleView('chart')"
          >
            <span v-if="isLoadingChart" class="animate-spin rounded-full h-3 w-3 border-b-2 border-current mr-1"></span>
            <span v-else class="i-aa-chart-bar mr-1"></span>{{ isLoadingChart ? 'Generating...' : 'Chart' }}
          </AaButton>
        </div>
      </div>

      <!-- Chart Generation Status -->
      <div v-if="isLoadingChart && !chartError" class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700">
        <div class="flex items-center space-x-2">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <div class="flex-1 text-sm">
            Generating chart
          </div>
        </div>
      </div>

      <!-- Chart Error Display -->
      <div v-if="chartError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600">
        <div class="flex items-start space-x-2">
          <span class="flex-shrink-0 w-4 h-4 i-aa-alert-triangle"></span>
          <div class="flex-1 text-sm">
            {{ chartError }}
            <button 
              @click="generateChart" 
              class="ml-2 text-blue-600 hover:text-blue-800 underline"
              :disabled="isLoadingChart"
            >
              Try again
            </button>
          </div>
        </div>
      </div>

      <!-- Table View -->
      <div v-if="result.count > 0 && viewMode === 'table'" class="border border-core-border-default rounded overflow-hidden">
        <div class="overflow-auto" style="max-height: 340px;">
          <table class="w-full text-sm table-fixed">
            <thead class="sticky top-0 z-10 shadow-sm">
              <tr class="bg-core-surface-secondary">
                <th 
                  v-for="header in result.headers" 
                  :key="header"
                  class="px-3 py-3 text-left text-core-content-primary font-medium border-b-2 border-core-border-default"
                  style="background-color: rgb(249, 250, 251);"
                >
                  {{ header }}
                </th>
              </tr>
            </thead>
            <tbody class="bg-white">
              <tr 
                v-for="(row, rowIndex) in result.rows" 
                :key="rowIndex"
                class="hover:bg-core-surface-secondary border-b border-core-border-default last:border-b-0"
              >
                <td 
                  v-for="(cell, cellIndex) in row" 
                  :key="cellIndex"
                  class="px-3 py-2 text-core-content-primary overflow-hidden text-ellipsis"
                >
                  {{ cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Chart View -->
      <div v-else-if="result.count > 0 && viewMode === 'chart'" class="border border-core-border-default rounded">
        <div v-if="isLoadingChart" class="p-8 text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <AaText element="p" class="text-sm text-core-content-secondary">
            Generating chart...
          </AaText>
        </div>
        <div v-else-if="chartImageUrl" class="p-4">
          <img 
            :src="chartImageUrl" 
            alt="Generated Chart" 
            class="max-w-full h-auto mx-auto rounded"
            style="max-height: 500px;"
          />
        </div>
        <div v-else class="p-8 text-center text-gray-500">
          <AaText element="p" class="text-sm">
            No chart available. Ready: {{ chartReady }}, URL: {{ !!chartImageUrl }}
          </AaText>
        </div>
      </div>
      
      <div v-else-if="result.count === 0" class="p-4 text-center text-core-content-secondary bg-core-surface-secondary rounded">
        No results found
      </div>
    </div>
  </div>
</template> 