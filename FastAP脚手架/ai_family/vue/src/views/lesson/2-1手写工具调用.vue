<template>
  <!-- 左侧提交问题，右侧展示本次实际调用与最终回答。 -->
  <div class="manual-tool-page">
    <!-- 输入区只负责提交当前问题。 -->
    <section class="panel question-panel">
      <!-- 页面标题对应本节功能。 -->
      <h3>手写一轮工具调用</h3>
      <!-- 明确天气来源，避免把固定数值误认为实时天气。 -->
      <p class="hint">天气工具返回教学模拟数据，非实时天气。</p>
      <!-- 长度与后端保持一致，等待期间不重复编辑和提交。 -->
      <el-input v-model="question" type="textarea" :rows="5" :maxlength="2000" :disabled="busy" />
      <!-- 发送时显示加载状态，最多等待两次模型请求完成。 -->
      <el-button type="primary" :loading="busy" :disabled="busy" @click="send">发送</el-button>
    </section>
    <!-- 回答与工具记录仅对应当前这次请求。 -->
    <section class="panel result-panel">
      <!-- 展示区域标题。 -->
      <h3>本次结果</h3>
      <!-- 请求期间说明尚未完成，不展示伪造的工具结果。 -->
      <p v-if="busy" class="hint">正在等待模型与工具返回。</p>
      <!-- 有成功结果后展示工具调用。 -->
      <template v-if="result">
        <!-- 无调用时明确显示空结果，不把普通回复伪装成工具执行。 -->
        <p v-if="!result.toolCalls.length" class="hint">本次没有调用工具。</p>
        <!-- 使用真实调用编号区分同轮中的多个调用。 -->
        <div v-for="call in result.toolCalls" :key="call.toolCallId" class="tool-card">
          <!-- 展示模型选择且后端已经执行的工具名。 -->
          <strong>{{ call.toolName }}</strong>
          <!-- 调用编号用于把请求与工具结果配对。 -->
          <p class="hint">调用编号：{{ call.toolCallId }}</p>
          <!-- 对象格式化后以纯文本展示。 -->
          <p>调用参数</p>
          <pre>{{ formatJson(call.arguments) }}</pre>
          <!-- 展示后端函数实际返回的数据。 -->
          <p>执行结果</p>
          <pre>{{ formatJson(call.result) }}</pre>
        </div>
        <!-- 最终回答按 Markdown 渲染，字号与聊天正文一致。 -->
        <h4>最终回答</h4>
        <div class="markdown-content" v-html="renderMarkdown(result.answer)"></div>
      </template>
      <!-- 只有未发送且无结果时才显示初始提示。 -->
      <p v-else-if="!busy" class="hint">发送问题后查看工具名称、参数、结果和回答。</p>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'

// 首次打开填入带城市的问题，便于观察模型提取参数。
const question = ref('杭州天气怎么样？')
// 只保留本轮成功结果，刷新后清空。
const result = ref(null)
// 控制加载状态和重复提交。
const busy = ref(false)

// 输入普通对象，返回带缩进的 JSON 字符串，仅用于展示。
function formatJson(value) {
  // 两个空格缩进，保留原始字段和值。
  return JSON.stringify(value, null, 2)
}

// 输入模型回答，转义原始 HTML 再解析 Markdown，返回渲染字符串。
function renderMarkdown(text) {
  // 不把模型直接返回的 HTML 标签作为页面元素执行。
  const escaped = (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 开启常用表格语法，段落与代码块交给 Markdown 控制。
  return marked.parse(escaped, { gfm: true, breaks: false, async: false })
}

// 无输入参数，读取当前问题，提交后更新本轮结果；失败由统一请求封装提示。
async function send() {
  // 正在请求时不重复发送。
  if (busy.value) return
  // 空白问题直接提示，避免无效模型调用。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 从发送开始锁定输入和按钮。
  busy.value = true
  // 清空上轮结果，避免本轮失败时误看成成功。
  result.value = null
  // 接口失败时仍要恢复页面状态。
  try {
    // 请求只发送问题；延长等待时间，为两次模型请求留出余量。
    const response = await request.post(
      // 与后端路由完整对应。
      '/api/manual-tool/chat',
      // 不把模型选择或工具结果交给前端伪造。
      { question: question.value },
      // 本节最多有两次模型请求，使用 120 秒 HTTP 等待时间。
      { timeout: 120000 }
    )
    // 业务成功才展示本轮结果。
    if (response.code === '200') result.value = response.data
  // 错误已经由 request 的公共拦截器提示，不重复弹窗。
  } catch {
  // 无论成功或失败都解锁输入与发送。
  } finally {
    // 本轮请求结束。
    busy.value = false
  }
}
</script>
<style scoped>
/* 输入与结果左右排列，小屏时允许换成上下排列。 */
.manual-tool-page { display: grid; grid-template-columns: minmax(260px, 1fr) minmax(0, 2fr); gap: 20px; align-items: start; }
/* 使用白底与内边距，并阻止长内容撑开网格。 */
.panel { background: white; padding: 20px; border-radius: 10px; min-width: 0; font-size: 14px; }
/* 说明文字使用较轻颜色。 */
.hint { color: #64748b; font-size: 13px; overflow-wrap: anywhere; }
/* 每次实际调用独立分组。 */
.tool-card { background: #f3f4f6; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
/* 工具参数与结果保留缩进，长行横向滚动。 */
pre { margin: 6px 0; padding: 10px; background: #e5e7eb; border-radius: 6px; font: 13px/1.7 Consolas, monospace; overflow-x: auto; white-space: pre; }
/* 提交按钮与输入框留出间隔。 */
.el-button { margin-top: 12px; }
/* 正文统一 14px，普通段落不用 pre-wrap，避免 Markdown 产生额外空白。 */
.markdown-content { font-size: 14px; line-height: 1.7; overflow-wrap: anywhere; }
/* v-html 的内部元素通过 deep 接收 scoped 样式。 */
.markdown-content :deep(p) { margin: 6px 0; }
/* 限制回答标题字号。 */
.markdown-content :deep(h1) { font-size: 20px; }
.markdown-content :deep(h2) { font-size: 18px; }
.markdown-content :deep(h3), .markdown-content :deep(h4), .markdown-content :deep(h5), .markdown-content :deep(h6) { font-size: 16px; }
/* 列表保留必要缩进。 */
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 24px; }
/* 代码使用小字号等宽字体。 */
.markdown-content :deep(code) { font: 13px/1.7 Consolas, monospace; background: #e5e7eb; padding: 2px 4px; }
/* 代码块保留原始空格，不撑开页面。 */
.markdown-content :deep(pre) { padding: 12px; background: #e5e7eb; overflow-x: auto; white-space: pre; overflow-wrap: normal; }
/* 代码块内部不再叠加行内代码内边距。 */
.markdown-content :deep(pre code) { padding: 0; background: transparent; }
/* 表格过宽时在正文内滚动。 */
.markdown-content :deep(table) { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; }
/* 表格单元格保留边框与间距。 */
.markdown-content :deep(th), .markdown-content :deep(td) { border: 1px solid #cbd5e1; padding: 6px 10px; }
/* 回答中的图片不超过正文宽度。 */
.markdown-content :deep(img) { max-width: 100%; }
/* 窄屏把输入和结果改成单列。 */
@media (max-width: 900px) { .manual-tool-page { grid-template-columns: 1fr; } }
</style>

