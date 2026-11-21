<template>
  <div class="shop-page">
    <h3>框架声明工具，查询商品与订单</h3>
    <!-- 固定模拟数据不代表实时商城状态。 -->
    <p>商品与订单工具返回模拟数据，非实时商城数据。</p>
    <!-- 输入本轮问题，等待时禁用。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="2000" :disabled="busy" />
    <!-- 完整回答返回前保持加载状态。 -->
    <el-button class="send-button" type="primary" :loading="busy" :disabled="busy" @click="send">发送</el-button>
    <!-- 区分尚未提交和本次没有执行工具。 -->
    <section v-if="completed" class="current-result">
      <!-- 工具记录仅属于当前提交。 -->
      <h4>本次工具执行记录</h4>
      <!-- 模型直接回答或追问时，不构造虚假的工具调用。 -->
      <p v-if="!toolCalls.length">本次没有调用工具</p>
      <!-- 同名工具可能执行多次，使用实际顺序索引展示。 -->
      <div v-for="(call, index) in toolCalls" :key="index" class="tool-card">
        <!-- 展示工具名称和模型原始调用编号。 -->
        <strong>{{ index + 1 }}. {{ call.toolName }}</strong>
        <p>调用编号：{{ call.toolCallId }}</p>
        <!-- 参数和结果以纯文本 JSON 展示，不作为 HTML 执行。 -->
        <div>调用参数</div>
        <pre>{{ JSON.stringify(call.arguments, null, 2) }}</pre>
        <div>执行结果</div>
        <pre>{{ JSON.stringify(call.result, null, 2) }}</pre>
      </div>
      <!-- 最终回答使用 Markdown，工具 JSON 保持纯文本。 -->
      <h4>最终回答</h4>
      <div class="content markdown-content" v-html="renderMarkdown(answer)"></div>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'

// 默认示例同时包含两个查询需求，便于观察多工具调用。
const question = ref('耳机多少钱？订单 DEMO1001 是什么状态？')
// 生成期间禁用输入，避免重复提交。
const busy = ref(false)
// 本次工具记录，每次发送前清空。
const toolCalls = ref([])
// 收到成功响应后才展示当前执行区。
const completed = ref(false)
// 本次最终回答。
const answer = ref('')
// 输入回答正文，转义原始 HTML 后解析 Markdown。
function renderMarkdown(text) {
  // 原始标签按文本处理，避免被作为页面元素执行。
  const escaped = (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 同步解析 GFM，普通换行由 Markdown 段落处理。
  return marked.parse(escaped, { gfm: true, breaks: false, async: false })
}

// 无输入参数，提交当前问题，成功后更新回答和实际工具记录。
async function send() {
  // 生成期间不重复请求。
  if (busy.value) return
  // 拒绝只有空白的输入。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 禁用输入和按钮。
  busy.value = true
  // 清除上一轮记录，避免误认为本轮执行结果。
  toolCalls.value = []
  // 本次尚未完成。
  completed.value = false
  // 清空上次回答。
  answer.value = ''
  // 普通 POST 等待整个工具调用过程结束。
  try {
    // 多轮模型和工具请求可能比普通聊天久，仅本次使用 180 秒超时。
    const result = await request.post('/api/shop-tools/chat', { question: question.value }, { timeout: 180000 })
    // 业务失败时保留用户输入，不展示成功记录。
    if (result.code !== '200') return
    // 只采用服务端返回的真实执行记录。
    toolCalls.value = result.data.toolCalls
    // 最终文字由模型根据本次工具结果生成。
    answer.value = result.data.answer
    // 本轮完成，允许展示没有工具调用的情况。
    completed.value = true
  // 公共请求封装已经提示错误。
  } catch {
  // 成功或失败都恢复输入。
  } finally {
    // 结束加载状态。
    busy.value = false
  }
}

</script>
<style scoped>
/* 聊天正文和工具记录统一使用 14px，避免标题挤占阅读区域。 */
.shop-page { background: white; padding: 20px; border-radius: 10px; font-size: 14px; }
/* 每组记录独立留出间距，内容按可用宽度折行。 */
.message, .tool-card { background: #f3f4f6; border-radius: 8px; padding: 12px; margin: 12px 0; min-width: 0; }
/* 用户原文保留换行，助手 Markdown 交给标签控制排版。 */
.user-content { white-space: pre-wrap; }
/* 长订单号与文本允许折行。 */
.content { margin-top: 6px; font-size: 14px; line-height: 1.7; overflow-wrap: anywhere; }
/* 工具 JSON 保留缩进，长行只在代码区滚动。 */
pre { padding: 10px; background: #e5e7eb; border-radius: 6px; overflow: auto; font-size: 13px; white-space: pre; }
/* v-html 的元素需要 deep 才能应用 scoped 样式。 */
.markdown-content :deep(p) { margin: 6px 0; }
/* Markdown 标题也限制字号。 */
.markdown-content :deep(h1) { font-size: 20px; }
.markdown-content :deep(h2) { font-size: 18px; }
.markdown-content :deep(h3), .markdown-content :deep(h4), .markdown-content :deep(h5), .markdown-content :deep(h6) { font-size: 16px; }
/* 标题使用紧凑间距。 */
.markdown-content :deep(h1), .markdown-content :deep(h2), .markdown-content :deep(h3), .markdown-content :deep(h4), .markdown-content :deep(h5), .markdown-content :deep(h6) { margin: 12px 0 6px; line-height: 1.4; }
/* 列表保留缩进。 */
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 24px; margin: 6px 0; }
/* 代码使用等宽小字号，块级代码允许横向滚动。 */
.markdown-content :deep(code) { font-family: Consolas, monospace; font-size: 13px; }
.markdown-content :deep(pre) { overflow: auto; white-space: pre; }
/* 表格宽于对话时只在表格区域滚动。 */
.markdown-content :deep(table) { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; }
.markdown-content :deep(th), .markdown-content :deep(td) { border: 1px solid #cbd5e1; padding: 6px 10px; }
/* 图片不突破消息边界。 */
.markdown-content :deep(img) { max-width: 100%; }
/* 发送按钮与输入框之间留出距离。 */
.send-button { margin-top: 12px; }
</style>

