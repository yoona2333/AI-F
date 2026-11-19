<template>
  <div class="chat-page">
    <h3>多轮对话与 MySQL 会话记忆</h3>
    <div v-for="item in messages" :key="item.id" class="message">
      <strong>{{ item.role === 'user' ? '用户：' : '聊天助手：' }}</strong>
      <div v-if="item.role === 'assistant'" class="content markdown-content" v-html="renderMarkdown(item.content)"></div>
      <div v-else class="content user-content">{{ item.content }}</div>
    </div>
    <el-input v-model="question" type="textarea" :rows="3" :disabled="busy" />
    <el-button type="primary" :loading="busy" :disabled="busy" @click="send">发送</el-button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'


const messages = ref([])
const question = ref('我叫小林，买耳机的预算是 300 元。')
const busy = ref(true)


function renderMarkdown(text) {
  const escaped = (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return marked.parse(escaped, { gfm: true, breaks: false, async: false })
}

async function loadMessages() {
  const result = await request.get('/api/memory/messages')
  // 业务成功时才使用返回的数据。
  if (result.code === '200') 
  messages.value = result.data
}

// 发送当前问题；成功后恢复数据库消息，失败时保留输入。
async function send() {
  if (busy.value) return
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  busy.value = true
  try {
    const result = await request.post('/api/memory/chat', { question: question.value })
    if (result.code !== '200') return
    // 成功后清空已发送的输入。
    question.value = ''
    // 重新查询数据库，渲染刚保存的完整问答。
    await loadMessages()
  // 公共请求封装已提示错误，这里不重复弹窗。
  } catch {
  // 无论请求成功或失败，都恢复页面操作。
  } finally {
    // 本轮等待结束。
    busy.value = false
  }
}

// 页面打开和刷新时读取 MySQL 中的历史。
onMounted(async () => {
  try {
    await loadMessages()
  } catch {
  } finally {
    busy.value = false
  }
})
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
