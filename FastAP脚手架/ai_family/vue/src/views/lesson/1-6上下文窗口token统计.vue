<template>
  <div class="usage-page">
    <el-card>
      <!-- 标题说明本节功能。 -->
      <h3>上下文与本次调用统计</h3>
      <!-- 提供两组预算值，便于观察裁剪。 -->
      <p>固定历史包含姓名和预算。将输入粗估阈值从 2000 改成 400，观察第一轮是否不再发送。</p>
      <!-- 展示裁剪前的固定历史，实际带入条数看后端统计。 -->
      <pre class="history-preview">{{ JSON.stringify(history, null, 2) }}</pre>
      <!-- 标签宽 110px，使预算和问题输入对齐。 -->
      <el-form label-width="110px">
        <!-- 绑定整数预算，限制 300～12000，步长 100，等待时禁用。 -->
        <el-form-item label="输入粗估阈值"><el-input-number v-model="budget" :min="300" :max="12000" :step="100" :precision="0" :disabled="busy" /></el-form-item>
        <!-- 绑定当前问题，三行文本框，最多 2000 字，等待时禁用。 -->
        <el-form-item label="本轮问题"><el-input v-model="question" type="textarea" :rows="3" maxlength="2000" :disabled="busy" /></el-form-item>
      </el-form>
      <!-- 点击调用 send，等待期间显示加载状态并禁用按钮。 -->
      <el-button class="send-button" type="primary" :loading="busy" :disabled="busy" @click="send">调用并查看统计</el-button>
    </el-card>
    <!-- 实际统计和发送前估算分开展示，缺失 usage 不展示零。 -->
    <el-card v-if="result" class="usage-result">
      <!-- 按纯文本展示本次完整回答并保留换行。 -->
      <div class="answer-text">{{ result.answer }}</div>
      <!-- 带边框的双列统计表，标题说明范围为本次调用。 -->
      <el-descriptions title="本次统计" :column="2" border>
        <!-- 可选链允许 usage 为 null；空值提示未返回，零值正常显示。 -->
        <el-descriptions-item label="实际输入 Token">{{ result.usage?.inputTokens ?? '服务未返回' }}</el-descriptions-item>
        <!-- 读取服务的输出用量，不按回答字数推算。 -->
        <el-descriptions-item label="实际输出 Token">{{ result.usage?.outputTokens ?? '服务未返回' }}</el-descriptions-item>
        <!-- 总量直接取自服务，缺失时不自行填零。 -->
        <el-descriptions-item label="实际总 Token">{{ result.usage?.totalTokens ?? '服务未返回' }}</el-descriptions-item>
        <!-- 后端模型调用耗时，单位毫秒。 -->
        <el-descriptions-item label="模型调用耗时">{{ result.elapsedMs }} ms</el-descriptions-item>
        <!-- 此项是发送前粗估，与实际输入用量不同。 -->
        <el-descriptions-item label="输入粗略估算">{{ result.estimatedInputTokens }}</el-descriptions-item>
        <!-- 移除的历史数量，按整轮增加两条。 -->
        <el-descriptions-item label="移除历史消息">{{ result.trimmedMessages }} 条</el-descriptions-item>
        <!-- 不包含 System 和当前问题。 -->
        <el-descriptions-item label="保留历史消息">{{ result.sentHistoryMessages }} 条</el-descriptions-item>
        <!-- STOP 通常表示正常结束，LENGTH 表示达到输出上限。 -->
        <el-descriptions-item label="结束原因">{{ result.finishReason }}</el-descriptions-item>
      </el-descriptions>
      <!-- 明确粗估值的使用范围。 -->
      <p>估算按 UTF-8 字节数加余量计算，不是千问分词结果，不用于核算费用。</p>
    </el-card>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 预算是本节用于观察裁剪的估算阈值，不是模型官方窗口。
const budget = ref(2000)
// 本轮问题固定问姓名和预算，便于观察哪些历史被移除。
const question = ref('我叫什么名字？现在买耳机的预算是多少？不知道就说不知道。')
// 四条示例历史构成两轮；每次请求相同，便于对比不同预算。
const history = [
  // 第一轮提问，包含姓名。
  { role: 'user', content: '我叫小林，我经常坐地铁上下班。' },
  // 第一轮回答，确认姓名和通勤需求。
  { role: 'assistant', content: '知道了，你叫小林，可以关注通勤场景的耳机。' },
  // 第二轮提问，包含预算。
  { role: 'user', content: '我现在买耳机的预算是 300 元，想要主动降噪。' },
  // 第二轮回答，确认预算和降噪需求。
  { role: 'assistant', content: '好的，你的预算是 300 元，关注主动降噪功能。' },
]
// 本次结果和等待状态；不把多次调用用量累加成单次统计。
const result = ref(null)
// 等待期间禁用输入和按钮，避免重复调用。
const busy = ref(false)

// 无输入参数，发送当前问题、历史和预算，更新本次统计；失败由公共请求封装提示。
async function send() {
  // 已有请求时不重复发送。
  if (busy.value) return
  // 拒绝空白问题，后端也会校验。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 输入被清空时可能不是整数，先给出提示。
  if (!Number.isInteger(budget.value)) return ElMessage.warning('请填写整数预算')
  // 开始等待本轮结果。
  busy.value = true
  // 清除旧统计，避免误认为是本次结果。
  result.value = null
  // 请求结束后无论成功与否都要恢复操作。
  try {
    // 只调用一次接口，同时取得回答和统计。
    const response = await request.post('/api/usage/chat', { question: question.value, history, contextBudget: budget.value })
    // 仅成功时使用返回的 data。
    if (response.code === '200') result.value = response.data
  // 公共请求封装已经提示失败，不重复弹窗。
  } catch {
  // 成功或失败都解除等待。
  } finally {
    // 恢复输入和发送按钮。
    busy.value = false
  }
}
</script>
<style scoped>
/* 卡片上下排列，间距 18px，正文使用 14px 字号。 */
.usage-page { display: grid; gap: 18px; font-size: 14px; }
/* 标题略大于正文。 */
.usage-page h3 { font-size: 16px; }
/* 示例 JSON 保留换行，长文本可折行，使用浅灰背景和 13px 字号。 */
.history-preview { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f4f6; padding: 12px; font-size: 13px; }
/* 回答保留换行，行高方便阅读，与统计表留出间距。 */
.answer-text { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14px; line-height: 1.7; margin-bottom: 16px; }
</style>

