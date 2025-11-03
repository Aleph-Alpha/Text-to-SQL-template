<script lang="ts" setup>
import { AaText } from '@aleph-alpha/ds-components-vue'
import { computed } from 'vue'
import { formatSQL } from '@/utils/sqlFormatter'

const props = defineProps<{
  sql: string
  title?: string
  showCopy?: boolean
}>()

const formattedSQL = computed(() => {
  return formatSQL(props.sql)
})

function copyToClipboard() {
  navigator.clipboard.writeText(props.sql).then(() => {
    console.log('SQL copied to clipboard')
  }).catch(err => {
    console.error('Failed to copy SQL:', err)
  })
}
</script>

<template>
  <div class="sql-display">
    <div v-if="title" class="flex items-center justify-between mb-2">
      <AaText element="h5" class="text-sm font-medium text-core-content-secondary">
        {{ title }}
      </AaText>
      <button
        v-if="showCopy"
        @click="copyToClipboard"
        class="text-xs text-core-content-tertiary hover:text-core-content-secondary flex items-center px-2 py-1 rounded hover:bg-core-surface-secondary transition-colors whitespace-nowrap flex-shrink-0"
        title="Copy SQL to clipboard"
      >
        <span class="i-aa-copy w-3 h-3 mr-1"></span>Copy
      </button>
    </div>
    
    <div class="bg-core-bg-primary border border-core-border-default p-3 rounded overflow-x-auto text-sm font-mono">
      <pre class="whitespace-pre-wrap text-core-content-primary"><code class="sql-code">{{ formattedSQL }}</code></pre>
    </div>
  </div>
</template>

<style scoped>
.sql-code {
  line-height: 1.5;
}
</style>
