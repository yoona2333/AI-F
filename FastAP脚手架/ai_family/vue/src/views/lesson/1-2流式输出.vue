<template>
  <div class="bench">
    <!-- 左：参数面板，与同步对话页保持同一套仪表语言 -->
    <section class="panel bench-controls">
      <header class="panel-head">
        <span class="eyebrow">参数面板</span>
        <h2 class="panel-title">发起一次流式调用</h2>
        <p class="panel-desc">模型生成一部分，页面就显示一部分</p>
      </header>

      <div class="field">
        <div class="field-head">
          <label for="stream-question">问题</label>
          <span class="mono field-key">Question</span>
        </div>
        <el-input
          id="stream-question"
          v-model="form.question"
          type="textarea"
          :rows="5"
          maxlength="2000"
          show-word-limit
          aria-label="问题"
          placeholder="比如：用三句话解释什么是 RAG"
        />
      </div>

      <div class="dial">
        <div class="dial-head">
          <span class="dial-name">temperature</span>
          <span class="dial-value mono">{{ Number(form.temperature).toFixed(1) }}</span>
        </div>
        <el-slider v-model="form.temperature" :min="0" :max="1.9" :step="0.1" aria-label="温度" />
        <p class="dial-tip">越低回答越稳定，越高越发散、越有创意</p>
      </div>

      <div class="dial">
        <div class="dial-head">
          <span class="dial-name">topP</span>
          <span class="dial-value mono">{{ Number(form.topP).toFixed(2) }}</span>
        </div>
        <el-slider v-model="form.topP" :min="0.1" :max="1" :step="0.05" aria-label="核采样" />
        <p class="dial-tip">只从累计概率达到 topP 的候选词里挑选</p>
      </div>

      <div class="dial">
        <div class="dial-head">
          <span class="dial-name">maxTokens</span>
          <span class="mono field-key">Output cap</span>
        </div>
        <el-input-number
          v-model="form.maxTokens"
          :min="1"
          :max="4096"
          :step="64"
          aria-label="最大输出 Token 数"
        />
        <p class="dial-tip">设成 20 就能很快看到被截断的效果</p>
      </div>

      <div class="actions">
        <el-button type="primary" size="large" :loading="loading" @click="send">发送</el-button>
      </div>
    </section>

    <!-- 右：输出面板，状态条直接告诉你看哪 -->
    <section class="panel bench-output">
      <header class="panel-head panel-head--row">
        <div>
          <span class="eyebrow">输出</span>
          <h2 class="panel-title">本次回答</h2>
        </div>
        <span class="phase" :class="`phase--${phase}`">{{ phaseText }}</span>
      </header>

      <div v-if="phase === 'waiting'" class="calling">
        <div class="calling-bar"><i></i></div>
        <p>已经发出请求，等待模型吐出第一段文字…</p>
      </div>

      <div v-else-if="!answer" class="placeholder">
        <p class="placeholder-title mono">No output yet</p>
        <p class="placeholder-text">流式调用会把模型生成的每一小段立刻显示出来，不用等整段写完。</p>
      </div>

      <article v-else class="answer">
        <div class="answer-body" v-html="answerHtml"></div>
      </article>

      <!-- 结束原因读数：STOP 正常结束，LENGTH 撞到上限被截断 -->
      <dl v-if="finishReason" class="readout">
        <div>
          <dt>finish</dt>
          <dd :class="finishReason === 'LENGTH' ? 'is-warn' : 'is-ok'">{{ finishReason }}</dd>
        </div>
        <div class="col-model">
          <dt>model</dt>
          <dd :title="modelName">{{ modelName || '—' }}</dd>
        </div>
        <div>
          <dt>tokens</dt>
          <dd :title="tokenDetail">{{ tokenText }}</dd>
        </div>
        <div>
          <dt>temp</dt>
          <dd>{{ form.temperature }}</dd>
        </div>
        <div>
          <dt>max</dt>
          <dd>{{ form.maxTokens }}</dd>
        </div>
        <div>
          <dt>chunks</dt>
          <dd>{{ chunkCount }}</dd>
        </div>
      </dl>

      <p v-if="finishReason === 'LENGTH'" class="truncate-note">
        回答在 maxTokens 处被截断，把上限调大就能拿到完整内容。
      </p>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { streamRequest } from '@/utils/stream'

// 问题初始为空；三个参数与后端校验范围一致
const form = reactive({ question: '', temperature: 0.7, topP: 0.8, maxTokens: 1024 })

const answer = ref('')
const answerHtml = computed(() => marked.parse(answer.value || ''))
const loading = ref(false)

// 页面阶段：idle 未提问 / waiting 等待首包 / streaming 正在生成 / done 结束 / error 失败
const phase = ref('idle')
const finishReason = ref('')
const errorMessage = ref('')
const chunkCount = ref(0)
// 结束事件里带来的模型名和 token 用量
const modelName = ref('')
const usage = ref(null)

// 总 token 数；没拿到用量时显示占位符，不假装是 0
const tokenText = computed(() => (usage.value ? usage.value.total_tokens : '—'))
// 鼠标悬停时补充输入/输出的明细
const tokenDetail = computed(() =>
  usage.value ? `输入 ${usage.value.input_tokens} / 输出 ${usage.value.output_tokens}` : '未返回用量',
)

const phaseText = computed(() => {
  if (phase.value === 'waiting') return '等待首包'
  if (phase.value === 'streaming') return '正在生成'
  if (phase.value === 'done') return finishReason.value === 'LENGTH' ? '已达上限' : '生成结束'
  if (phase.value === 'error') return '生成失败'
  return '等待提问'
})

async function send() {
  if (loading.value) return

  if (!form.question.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  answer.value = ''
  chunkCount.value = 0
  finishReason.value = ''
  errorMessage.value = ''
  modelName.value = ''
  usage.value = null
  loading.value = true
  phase.value = 'waiting'

  try {
    await streamRequest('/api/chat/stream', {
      data: { ...form },
      onEvent: ({ event, data }) => {
        if (event === 'message') {
          // 增量直接追加，不攒成完整回答再渲染
          answer.value += data.content
          chunkCount.value += 1
          phase.value = 'streaming'
        } else if (event === 'done') {
          // 保存 STOP、LENGTH 或 UNKNOWN
          finishReason.value = data.finishReason
          // 后端顺带返回的模型名与 token 用量，拿不到时保持空值
          modelName.value = data.modelName || ''
          usage.value = data.usage || null
        } else if (event === 'error') {
          throw new Error(data.message)
        }
      },
    })

    // 没有结束事件时，不能把连接关闭当成成功
    if (!finishReason.value) throw new Error('未收到结束事件，请重新发送')
    phase.value = 'done'
  } catch (error) {
    // 已经显示出来的正文保留，只把失败原因写在状态里
    errorMessage.value = error.message
    phase.value = 'error'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 两列布局，与 1-1 同步对话页一致 */
.bench {
  display: grid;
  grid-template-columns: 408px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.panel-head {
  margin-bottom: 20px;
}

.panel-head--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

/* 阶段标记：等宽小字 + 描边，颜色随状态变化 */
.phase {
  padding: 4px 9px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--ink-3);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  white-space: nowrap;
}

.phase--waiting,
.phase--streaming {
  color: var(--brand-3);
  border-color: color-mix(in srgb, var(--brand-3) 40%, white);
  background: #f2f7f9;
}

.phase--done {
  color: var(--ok);
  border-color: color-mix(in srgb, var(--ok) 35%, white);
  background: var(--ok-soft);
}

.phase--error {
  color: var(--signal);
  border-color: color-mix(in srgb, var(--signal) 35%, white);
  background: var(--signal-soft);
}

/* ---------- 输入区 ---------- */
.field-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}

.field-head label {
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
}

.field-key {
  color: var(--ink-4);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.field :deep(.el-textarea__inner) {
  padding: 10px 12px;
  color: var(--ink);
  font-family: var(--font-body);
  font-size: 13.5px;
  line-height: 1.7;
  border-radius: var(--radius);
  box-shadow: 0 0 0 1px var(--line) inset;
}

.field :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px var(--brand-2) inset;
}

.field :deep(.el-input__count) {
  color: var(--ink-4);
  font-family: var(--font-mono);
  font-size: 10px;
}

/* ---------- 旋钮 ---------- */
.dial {
  margin-top: 22px;
}

.dial-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}

.dial-name {
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.04em;
}

.dial-value {
  color: var(--ink);
  font-size: 18px;
  font-weight: 600;
  line-height: 1;
}

.dial-tip {
  margin: 2px 0 0;
  color: var(--ink-4);
  font-size: 11.5px;
  line-height: 1.6;
}

.dial :deep(.el-slider__runway) {
  height: 3px;
  margin: 12px 0;
  background: var(--line-2);
}

.dial :deep(.el-slider__bar) {
  height: 3px;
  background: var(--brand-2);
}

.dial :deep(.el-slider__button) {
  width: 13px;
  height: 13px;
  background: var(--surface);
  border: 2px solid var(--signal);
}

.dial :deep(.el-input-number) {
  width: 140px;
}

.dial :deep(.el-input__wrapper) {
  border-radius: var(--radius);
  box-shadow: 0 0 0 1px var(--line) inset;
}

/* ---------- 操作区 ---------- */
.actions {
  display: flex;
  gap: 10px;
  margin-top: 26px;
  padding-top: 20px;
  border-top: 1px solid var(--line-2);
}

.actions :deep(.el-button) {
  border-radius: var(--radius);
}

.actions :deep(.el-button--primary) {
  min-width: 104px;
  font-weight: 600;
}

/* ---------- 等待 / 空状态 ---------- */
.calling {
  padding: 36px 0;
  text-align: center;
}

.calling-bar {
  position: relative;
  overflow: hidden;
  width: 160px;
  height: 2px;
  margin: 0 auto 16px;
  background: var(--line-2);
}

.calling-bar i {
  position: absolute;
  top: 0;
  left: 0;
  width: 40%;
  height: 100%;
  background: var(--signal);
  animation: scan 1.15s ease-in-out infinite;
}

@keyframes scan {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(350%);
  }
}

.calling p {
  margin: 0;
  color: var(--ink-3);
  font-size: 12.5px;
}

.placeholder {
  padding: 56px 24px;
  text-align: center;
  background: var(--paper-2);
  border: 1px dashed var(--line);
  border-radius: var(--radius);
}

.placeholder-title {
  margin: 0;
  color: var(--ink-3);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.placeholder-text {
  max-width: 26em;
  margin: 12px auto 0;
  color: var(--ink-4);
  font-size: 12.5px;
  line-height: 1.7;
}

/* ---------- 正文 ---------- */
.answer {
  animation: rise 0.3s ease both;
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

.answer-body {
  max-width: 74ch;
  color: var(--ink-2);
  font-size: 14px;
  line-height: 1.85;
  overflow-wrap: anywhere;
}

.answer-body :deep(*:first-child) {
  margin-top: 0;
}

.answer-body :deep(p) {
  margin: 0 0 12px;
}

.answer-body :deep(h1),
.answer-body :deep(h2),
.answer-body :deep(h3) {
  margin: 22px 0 10px;
  color: var(--ink);
  font-size: 15px;
  font-weight: 600;
}

.answer-body :deep(ul),
.answer-body :deep(ol) {
  margin: 0 0 12px;
  padding-left: 20px;
}

.answer-body :deep(li) {
  margin-bottom: 5px;
}

.answer-body :deep(pre) {
  overflow-x: auto;
  margin: 0 0 14px;
  padding: 12px 14px;
  background: var(--paper-2);
  border: 1px solid var(--line-2);
  border-radius: var(--radius);
}

.answer-body :deep(code) {
  padding: 1px 5px;
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--signal-soft);
  border-radius: var(--radius);
}

.answer-body :deep(pre code) {
  padding: 0;
  color: var(--ink-2);
  background: none;
}

/* ---------- 读数条 ---------- */
.readout {
  display: grid;
  /* 模型名和 token 数比参数更值得占宽，其余等分 */
  grid-template-columns: 0.85fr 1.5fr 0.85fr 0.75fr 0.7fr 0.8fr;
  margin: 20px 0 0;
  overflow: hidden;
  background: var(--paper-2);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.readout > div {
  padding: 9px 12px;
  border-right: 1px solid var(--line-2);
}

.readout > div:last-child {
  border-right: 0;
}

.readout dt {
  color: var(--ink-4);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.readout dd {
  overflow: hidden;
  margin: 5px 0 0;
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.readout dd.is-ok {
  color: var(--ok);
}

.readout dd.is-warn {
  color: var(--warn);
}

.truncate-note {
  margin: 12px 0 0;
  padding: 9px 12px;
  color: var(--warn);
  font-size: 12px;
  background: var(--warn-soft);
  border-left: 2px solid var(--warn);
}

/* ---------- 响应式 ---------- */
@media (max-width: 1180px) {
  .bench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .readout {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .readout > div {
    border-bottom: 1px solid var(--line-2);
  }
}
</style>
