export function formatSQL(sql: string): string {
  if (!sql || typeof sql !== 'string') {
    return sql
  }

  let formatted = sql.trim().replace(/\s+/g, ' ')

  const newLineKeywords = [
    'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 
    'LIMIT', 'OFFSET', 'UNION', 'INTERSECT', 'EXCEPT'
  ]

  const joinKeywords = [
    'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'
  ]

  newLineKeywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi')
    formatted = formatted.replace(regex, `\n${keyword}`)
  })

  joinKeywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi')
    formatted = formatted.replace(regex, `\n${keyword}`)
  })

  const lines = formatted.split('\n').map(line => line.trim()).filter(line => line)
  
  const indentedLines = lines.map((line, index) => {
    if (index === 0) return line
    
    const noIndentKeywords = ['FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'UNION']
    const joinKeywords = ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN']
    
    if (noIndentKeywords.some(keyword => line.toUpperCase().startsWith(keyword))) {
      return line
    }
    
    if (joinKeywords.some(keyword => line.toUpperCase().startsWith(keyword))) {
      return `  ${line}`
    }
    
    return `  ${line}`
  })

  return indentedLines.join('\n').trim()
}

export function extractSQLFromText(text: string): string | null {
  if (!text) return null

  const codeBlockMatch = text.match(/```(?:sql)?\s*(.*?)\s*```/is)
  if (codeBlockMatch) {
    return codeBlockMatch[1].trim()
  }

  const selectMatch = text.match(/(SELECT\s+(?:(?!SELECT\s+)[\s\S])*?(?:;|$))/i)
  if (selectMatch) {
    return selectMatch[1].trim()
  }

  if (/^\s*(SELECT|INSERT|UPDATE|DELETE|WITH)\b/i.test(text)) {
    return text.trim()
  }

  return null
}
