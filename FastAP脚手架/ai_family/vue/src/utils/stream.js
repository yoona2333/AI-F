import { ElMessage } from 'element-plus'

/**
 * 流式请求（SSE）：基于 fetch 实现，支持 POST 请求体。
 * 不使用浏览器自带的 EventSource：它只能发 GET 请求，而且连接断开后会自动重连、重复提问。
 *
 * 用法：
 * await streamRequest('/api/xxx/stream', {
 *   data: { question: '你好' },
 *   onEvent: ({ event, data }) => { ... },
 * })
 *
 * 后端每条 SSE 事件的 data 统一发送 JSON，这里会自动解析成对象。
 */
export async function streamRequest(url, { method = 'POST', data, onEvent, signal } = {}) {
  let response
  try {
    response = await fetch(`${import.meta.env.VITE_BASE_URL}${url}`, {
      method,
      headers: {
        'Content-Type': 'application/json;charset=utf-8',
        Accept: 'text/event-stream, application/json',
      },
      body: data === undefined ? undefined : JSON.stringify(data),
      signal,
    })
  } catch (error) {
    if (error.name !== 'AbortError') {
      ElMessage.error('网络连接失败')
    }
    throw error
  }

  // 后端在开始推流之前出错时，返回的是普通 JSON 格式的 Result
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    const result = await response.json().catch(() => null)
    const message = result?.msg || `请求失败（HTTP ${response.status}）`
    ElMessage.error(message)
    throw new Error(message)
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) {
        break
      }
      // Spring Boot 用 \n 分隔事件，sse-starlette 用 \r\n 分隔，这里统一成 \n
      buffer = (buffer + value).replace(/\r\n/g, '\n')
      let boundary
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const event = parseEvent(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (event) {
          onEvent?.(event)
        }
      }
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      ElMessage.error('流式连接中断')
    }
    throw error
  }
}

function parseEvent(block) {
  let event = 'message'
  let id = ''
  const dataLines = []
  for (const line of block.split('\n')) {
    // 以冒号开头的是注释（例如心跳 ping），直接忽略
    if (!line || line.startsWith(':')) {
      continue
    }
    const colonIndex = line.indexOf(':')
    const field = colonIndex >= 0 ? line.slice(0, colonIndex) : line
    let value = colonIndex >= 0 ? line.slice(colonIndex + 1) : ''
    if (value.startsWith(' ')) {
      value = value.slice(1)
    }
    if (field === 'event') {
      event = value
    } else if (field === 'id') {
      id = value
    } else if (field === 'data') {
      dataLines.push(value)
    }
  }
  if (!dataLines.length) {
    return null
  }

  const rawData = dataLines.join('\n')
  let parsedData
  try {
    parsedData = JSON.parse(rawData)
  } catch {
    parsedData = rawData
  }
  return { event, id, data: parsedData }
}
