<template>
  <div class="chat-page">
    <h3>聊天助手</h3>
    <div v-for="item in messages" :key="item.id" class="message">
      <!-- 根据消息发言者显示用户或助手。 -->
      <strong>{{ item.role === 'user' ? '我' : '助手' }}</strong>
      <!-- 助手回答解析 Markdown，用户问题保留原始文本和换行。 -->
      <div v-if="item.role === 'assistant'" class="content markdown-content" v-html="renderMarkdown(item.content)"></div>
      <div v-else class="content user-content">{{ item.content }}</div>
    </div>
    <!-- 流式增量先展示在临时区域。 -->
    <div v-if="partial" class="message">
      <strong>助手</strong>
      <div class="content markdown-content" v-html="renderMarkdown(partial)"></div>
    </div>
    <!-- 统计来自本轮服务返回值，不保存到数据库。 -->
    <p v-if="usage">本轮 Token：输入 {{ usage.input_tokens }}，输出 {{ usage.output_tokens }}</p>
    <!-- 输入本轮问题，生成期间禁用。 -->
    <el-input v-model="question" type="textarea" :rows="3" :disabled="busy" />
    <!-- 生成期间显示加载状态，回复结束后恢复发送。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="send">发送</el-button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
// 沿用脚手架已有的 Markdown 解析器，无需新增依赖。
import { marked } from 'marked'
import request from '@/utils/request'

// 数据库中已经保存的聊天历史。
const messages = ref([])
// 示例问题，用户可以修改。
const question = ref('我叫小林，买耳机的预算是 300 元，请记住。')
// 尚未保存的流式回答文字。
const partial = ref('')
// 本轮实际用量，未返回时为空。
const usage = ref(null)
// 初次加载和生成期间禁用操作。
const busy = ref(true)

// 接收回答原文，转义原始 HTML 后解析 Markdown，不修改数据库中的正文。
function renderMarkdown(text) {
  // 转义 HTML 标签，避免模型返回的标签被作为页面元素执行。
  const escaped = (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 开启 GFM 表格等语法；普通换行不强制转换为额外的换行标签。
  return marked.parse(escaped, { gfm: true, breaks: false, async: false })
}

// 读取聊天历史，成功后更新消息列表。
async function loadMessages() {
  // 使用普通 request 获取统一 Result。
  const result = await request.get('/api/assistant/messages')
  // 业务成功才更新页面。
  if (result.code === '200') messages.value = result.data
}

// 页面加载时恢复已经保存的聊天消息。
async function restoreMessages() {
  // 读取期间禁止发送。
  busy.value = true
  // 清除上次临时回答。
  partial.value = ''
  // 初次加载时清空本轮统计。
  usage.value = null
  // 加载失败也要恢复按钮。
  try {
    // 读取数据库中的历史消息。
    await loadMessages()
  // 普通 request 已经显示错误提示。
  } catch {
  // 无论成功与否都结束等待。
  } finally {
    // 允许页面操作。
    busy.value = false
  }
}

// 提交问题，读取 SSE 增量，结束后恢复已保存历史。
async function send() {
  // 生成期间不重复发送。
  if (busy.value) return
  // 空白问题直接提示，不请求模型。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 禁用输入和发送，等待本轮完成。
  busy.value = true
  // 清空上轮临时回答。
  partial.value = ''
  // 清空上轮统计。
  usage.value = null
  // 捕获网络、服务和流式解析错误。
  try {
    // fetch 支持逐块读取；普通 axios 封装用于前面的历史查询。
    const response = await fetch(`${import.meta.env.VITE_BASE_URL}/api/assistant/stream`, {
      // POST 请求携带当前问题。
      method: 'POST',
      // 告诉后端请求正文为 JSON。
      headers: { 'Content-Type': 'application/json' },
      // 序列化请求数据，不发送页面历史。
      body: JSON.stringify({ question: question.value })
    })
    // 接口失败或没有可读正文时结束本轮。
    if (!response.ok || !response.body) throw new Error('请求失败')
    // 获取流读取器，每次读取可能只有半帧或包含多帧。
    const reader = response.body.getReader()
    // UTF-8 解码器处理跨网络块的中文字符。
    const decoder = new TextDecoder()
    // 缓冲尚未凑齐的 SSE 帧。
    let buffer = ''
    // done 事件表示后端已完成生成和保存。
    let finished = false
    // 反复读取网络块，直到响应流结束。
    while (true) {
      // done 是网络读取结束标记，不是业务 done 事件。
      const { value, done } = await reader.read()
      // 网络流结束时退出循环。
      if (done) break
      // 流式解码保留跨块中文字符，并追加到缓冲。
      buffer += decoder.decode(value, { stream: true })
      // SSE 帧由两个换行分隔。
      let end = buffer.indexOf('\n\n')
      // 同一个网络块中可能有多帧，逐个处理。
      while (end !== -1) {
        // 本节每帧只有一条 data 行，截取当前完整帧。
        const frame = buffer.slice(0, end)
        // 未处理的半帧留给下一次网络读取。
        buffer = buffer.slice(end + 2)
        // 去掉 data 前缀后解析 JSON。
        const data = JSON.parse(frame.slice(6))
        // 增量事件立即追加文字。
        if (data.type === 'delta') partial.value += data.content
        // 错误事件进入下方 catch，显示提示。
        if (data.type === 'error') throw new Error(data.message)
        // 业务完成事件包含本轮实际用量。
        if (data.type === 'done') {
          // 标记本轮成功完成。
          finished = true
          // 没有统计时保持空，不展示虚构数字。
          usage.value = data.usage
        }
        // 继续检查缓冲中是否还有完整帧。
        end = buffer.indexOf('\n\n')
      }
    }
    // 网络断开不能当作回复成功。
    if (!finished) throw new Error('回复未完成，请检查网络后刷新历史')
    // 读取数据库中刚保存的完整问答。
    await loadMessages()
    // 完整回答已进入历史，去掉临时文字避免重复显示。
    partial.value = ''
    // 只有成功后才清空问题。
    question.value = ''
  // 显示流式请求的错误；问题保留，便于检查后重试。
  } catch (error) {
    // 使用异常信息，未知错误显示默认提示。
    ElMessage.error(error.message || '生成失败')
  // 网络或服务失败时也要解除等待。
  } finally {
    // 本轮结束，允许下一次发送。
    busy.value = false
  }
}

// 页面初次加载恢复聊天历史。
onMounted(restoreMessages)
</script>

<style scoped>
/* 白底聊天区域，内边距留出阅读空间。 */
.chat-page { background: white; padding: 20px; border-radius: 10px; }
/* 每条发言有独立浅灰区域。 */
.message { background: #f3f4f6; padding: 12px; margin-bottom: 12px; border-radius: 8px; }
/* 发言者名称和正文统一使用较小字号。 */
.message > strong { font-size: 14px; }
/* 长文字可以折行，正文使用 14px 字号。 */
.content { margin-top: 6px; font-size: 14px; overflow-wrap: anywhere; line-height: 1.7; }
/* 只有用户纯文本保留原始换行；Markdown 交由段落和列表控制排版。 */
.user-content { white-space: pre-wrap; }
.markdown-content { white-space: normal; }
/* v-html 生成的元素需要使用 :deep，才能应用 scoped 样式。 */
.markdown-content :deep(p) { margin: 6px 0; }
/* 限制 Markdown 标题大小，避免对话中的标题过大。 */
.markdown-content :deep(h1) { font-size: 20px; }
.markdown-content :deep(h2) { font-size: 18px; }
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) { font-size: 16px; }
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) { margin: 12px 0 6px; line-height: 1.4; }
/* 列表保留缩进，引用使用浅色竖线。 */
.markdown-content :deep(ul),
.markdown-content :deep(ol) { margin: 6px 0; padding-left: 24px; }
.markdown-content :deep(blockquote) { margin: 8px 0; padding-left: 12px; border-left: 3px solid #cbd5e1; color: #64748b; }
/* 代码使用等宽小字号，代码块保留缩进，长行横向滚动。 */
.markdown-content :deep(code) { font-family: Consolas, Monaco, monospace; font-size: 13px; background: #e5e7eb; padding: 2px 4px; border-radius: 4px; }
.markdown-content :deep(pre) { margin: 8px 0; padding: 12px; background: #e5e7eb; border-radius: 6px; overflow-x: auto; white-space: pre; overflow-wrap: normal; }
.markdown-content :deep(pre code) { padding: 0; background: transparent; }
/* 表格保留边框，超宽时在正文区域滚动。 */
.markdown-content :deep(table) { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; margin: 8px 0; }
.markdown-content :deep(th),
.markdown-content :deep(td) { border: 1px solid #cbd5e1; padding: 6px 10px; }
/* 去掉正文首尾多余空白，图片不超出消息宽度。 */
.markdown-content :deep(> :first-child) { margin-top: 0; }
.markdown-content :deep(> :last-child) { margin-bottom: 0; }
.markdown-content :deep(img) { max-width: 100%; height: auto; }
/* 按钮与输入框留出间隔。 */
.el-button { margin-top: 12px; }
</style>
