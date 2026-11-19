<template>
  <div class="bench">
    
    <section class="panel bench-controls">
      <header class="panel-head">
        <span class="eyebrow">参数面板</span>
        <h2 class="panel-title">发起一次同步调用</h2>
        <p class="panel-desc">等模型生成完整回答后，一次性返回</p>
      </header>

      <div class="field">
        <div class="field-head">
          <label for="question-input">问题</label>
          <span class="mono field-key">Question</span>
        </div>
        <el-input
          id="question-input"
          v-model="form.question"
          type="textarea"
          :rows="5"
          maxlength="2000"
          show-word-limit
          aria-label="问题"
          placeholder="比如：用一句话解释什么是 RAG"
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

      <figure class="sampling">
        <figcaption class="sampling-head">
          <span class="mono">候选词分布</span>
          <span class="mono sampling-count">保留 {{ keptCount }} / {{ BAR_COUNT }}</span>
        </figcaption>
        <div class="band" aria-hidden="true">
          <i
            v-for="(bar, index) in bars"
            :key="index"
            class="bar"
            :class="{ 'is-cut': !bar.kept }"
            :style="{ height: `${bar.height}%` }"
          ></i>
        </div>
        <p class="sampling-note">柱高是候选词的相对概率；灰色部分被 topP 裁掉，模型不会从里面选字。</p>
      </figure>

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
        <p class="dial-tip">回答会在这个长度被截断，单位是 Token</p>
      </div>

      <div class="actions">
        <el-button type="primary" size="large" :loading="loading" @click="sendQuestion">
          发送
        </el-button>
        <el-button size="large" native-type="button" @click="resetParams">恢复默认参数</el-button>
      </div>
    </section>

    <!-- 右：输出面板，像一段仪表读数加正文 -->
    <section class="panel bench-output">
      <header class="panel-head panel-head--row">
        <div>
          <span class="eyebrow">输出</span>
          <h2 class="panel-title">本次回答</h2>
        </div>
      </header>

      <div v-if="loading" class="calling">
        <div class="calling-bar"><i></i></div>
        <p>同步调用要等全部内容生成完才会返回，先别走开。</p>
      </div>

      <div v-else-if="!result" class="placeholder">
        <p class="placeholder-title mono"></p>
        <p class="placeholder-text"></p>
        <div class="examples">
          <span class="examples-label mono">试试</span>
          <button
            v-for="example in examples"
            :key="example"
            type="button"
            class="example"
            @click="form.question = example"
          >
            {{ example }}
          </button>
        </div>
      </div>

      <article v-else class="answer">
        <p class="answer-q"><span class="q-mark">提问</span>{{ result.question }}</p>

        <dl class="readout">
          <div>
            <dt>model</dt>
            <dd>{{ result.modelName }}</dd>
          </div>
          <div>
            <dt>tokens</dt>
            <dd :title="tokenDetail">{{ tokenText }}</dd>
          </div>
          <div>
            <dt>temp</dt>
            <dd>{{ result.temperature }}</dd>
          </div>
          <div>
            <dt>top-p</dt>
            <dd>{{ result.topP }}</dd>
          </div>
          <div>
            <dt>max</dt>
            <dd>{{ result.maxTokens }}</dd> 
          </div>
          <div>
            <dt>finish</dt>
            <dd :class="result.finishReason === 'LENGTH' ? 'is-warn' : 'is-ok'">
              {{ result.finishReason }}
            </dd>
          </div>
        </dl>

        <p v-if="result.finishReason === 'LENGTH'" class="truncate-note">
          回答在 maxTokens 处被截断，把上限调大就能拿到完整内容。
        </p>

        <div class="answer-body" v-html="renderMarkdown(result.answer)"></div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request.js'

// 页面默认参数：温度 0.7、核采样 0.8、输出上限 1024；初始化和恢复操作共用
const DEFAULT_PARAMS = { temperature: 0.7, topP: 0.8, maxTokens: 1024 }

const form = reactive({
  question: '',
  ...DEFAULT_PARAMS,
})
///`ref` 用来定义**基础类型的响应式变量**（字符串、数字、布尔值 true/false）
///`reactive` 一般用来定义**对象 / 数组**。
const loading = ref(false)
const result = ref(null)

// token 用量：模型没返回时显示占位符，不显示 0
const tokenText = computed(() => (result.value?.usage ? result.value.usage.total_tokens : '—'))

// 悬停时补充输入/输出的拆分，标题属性不占版面
const tokenDetail = computed(() =>
  result.value?.usage
    ? `输入 ${result.value.usage.input_tokens} / 输出 ${result.value.usage.output_tokens}`
    : '未返回用量',
)

// 空状态里的示例问题：点一下就填进输入框，省得面对空白输入框发呆
const examples = [
  '用三句话解释什么是 RAG',
  'temperature 调高后回答会有什么不一样',
  '把「你好，世界」翻译成英文和日文',
]

/* ---------------- 候选词分布 ----------------
   用固定的伪随机种子生成 28 个候选词的相对分值，
   再按 softmax(分值 / 温度) 换算成概率，保证每次刷新形状一致、便于观察参数变化。 */
const BAR_COUNT = 28

const seededScores = (() => {
  let seed = 20260119
  const scores = []
  for (let i = 0; i < BAR_COUNT; i += 1) {
    seed = (seed * 1103515245 + 12345) % 2147483648
    scores.push(seed / 2147483648)
  }
  // 降序排列，让柱子从高到低铺开，像一张概率排序表
  return scores.sort((left, right) => right - left)
})()

const bars = computed(() => {
  // 温度为 0 时会出现除零，用 0.05 作为最小温度兜底
  const temperature = Math.max(0.05, Number(form.temperature) || 0)
  const weights = seededScores.map(score => Math.exp(score / temperature))
  const weightSum = weights.reduce((sum, weight) => sum + weight, 0)
  const probabilities = weights.map(weight => weight / weightSum)
  const peak = Math.max(...probabilities)

  // 按概率降序累计，起点仍在 topP 之内的柱子会被保留
  let cumulative = 0
  return probabilities.map(probability => {
    const startsAt = cumulative
    cumulative += probability
    return {
      height: Math.max(2, (probability / peak) * 100),
      kept: startsAt < Number(form.topP) - 1e-9,
    }
  })
})

const keptCount = computed(() => bars.value.filter(bar => bar.kept).length)

/* ---------------- 请求 ---------------- */

const sendQuestion = async () => {
  if (!form.question.trim()) {
    ElMessage.warning('请先输入问题')
    return
  }

  if (loading.value) return
  const payload = { ...form }
  result.value = null
  loading.value = true

  try {
    const res = await request.post('/api/chat/sync', payload)

    // 业务码为字符串 200 才算成功，HTTP 200 不能代替这个判断
    if (res.code === '200') {
      result.value = { question: payload.question, ...res.data }
    }
  } catch {
    // 请求拦截器已经弹出错误提示，这里不再重复提示
  } finally {
    loading.value = false
  }
}

const resetParams = () => {
  // 只恢复三个参数，保留用户已经写好的问题
  Object.assign(form, DEFAULT_PARAMS)
}

const renderMarkdown = text => marked.parse(text || '')
</script>

<style scoped>
/* 两列布局：左侧固定宽度放仪表控件，右侧留白给长段回答 */
.bench {
  display: grid;
  grid-template-columns: 408px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

/* ---------------- 面板头 ---------------- */

.panel-head {
  margin-bottom: 20px;
}

.panel-head--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

/* ---------------- 输入区 ---------------- */

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

/* 字段英文名：等宽小字，作为面板上的铭牌 */
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

/* ---------------- 旋钮 ---------------- */

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

/* 参数值用大号等宽数字，像仪表读数 */
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

/* 滑杆：细轨道 + 珊瑚色滑块，和整体仪表语言一致 */
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

/* ---------------- 候选词分布带 ---------------- */

.sampling {
  margin: 22px 0 0;
  padding: 14px 14px 12px;
  background: var(--paper-2);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.sampling-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  color: var(--ink-3);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sampling-count {
  color: var(--ink-2);
  letter-spacing: 0.04em;
}

/* 柱子自底部生长，高度用百分比，参数变化时平滑过渡 */
.band {
  display: flex;
  gap: 3px;
  align-items: flex-end;
  height: 64px;
  margin-top: 10px;
  padding-bottom: 1px;
  border-bottom: 1px solid var(--line-strong);
}

.bar {
  flex: 1;
  min-width: 2px;
  background: var(--signal);
  border-radius: 1px 1px 0 0;
  transition: height 0.28s ease, background 0.2s ease;
}

/* 被 topP 裁掉的候选词：退成纸面色，仅留轮廓 */
.bar.is-cut {
  background: var(--line);
}

.sampling-note {
  margin: 10px 0 0;
  color: var(--ink-4);
  font-size: 11px;
  line-height: 1.6;
}

/* ---------------- 操作区 ---------------- */

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
  /* 锁住宽度，避免加载图标出现时按钮抖动 */
  min-width: 104px;
  font-weight: 600;
}

/* ---------------- 等待状态 ---------------- */

.calling {
  padding: 36px 0;
  text-align: center;
}

/* 不确定进度的扫描条，用来表达「正在等完整结果」 */
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

/* ---------------- 空状态 ---------------- */

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

/* 示例问题：点击即可填入左侧输入框 */
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: center;
  margin-top: 22px;
}

.examples-label {
  color: var(--ink-4);
  font-size: 10px;
  letter-spacing: 0.14em;
}

.example {
  padding: 6px 11px;
  color: var(--ink-2);
  font-family: var(--font-body);
  font-size: 12px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}

.example:hover {
  color: var(--ink);
  background: #fff;
  border-color: var(--line-strong);
}

.example:active {
  background: var(--paper-2);
}

/* ---------------- 回答 ---------------- */

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

.answer-q {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin: 0;
  color: var(--ink);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.7;
}

/* 问题前的方框标记，替代「问：」这类弱标点 */
.q-mark {
  flex: 0 0 auto;
  padding: 1px 6px;
  color: var(--signal);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.6;
  border: 1px solid currentColor;
    border-radius: var(--radius);
}

/* 参数读数条：五格等宽，像设备铭牌 */
.readout {
  display: grid;
  /* 模型名和参数各占一格，token 数需要单独的窄列 */
  grid-template-columns: 1.3fr 0.8fr 0.8fr 0.7fr 0.7fr 0.8fr;
  margin: 18px 0 0;
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

/* 正文：控制行宽，长回答也能一行行读下去 */
.answer-body {
    max-width: 74ch;
    margin-top: 20px;
    color: var(--ink-2);
    font-size: 14px;
    line-height: 1.85;
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
    line-height: 1.5;
}

.answer-body :deep(ul),
.answer-body :deep(ol) {
    margin: 0 0 12px;
    padding-left: 20px;
}

.answer-body :deep(li) {
    margin-bottom: 5px;
}

.answer-body :deep(a) {
    color: var(--brand-3);
    text-decoration: underline;
    text-underline-offset: 2px;
}

.answer-body :deep(blockquote) {
    margin: 0 0 12px;
    padding: 2px 0 2px 14px;
    color: var(--ink-3);
    border-left: 2px solid var(--line-strong);
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

/* 代码块内的 code 不需要行内底色和内边距 */
.answer-body :deep(pre code) {
    padding: 0;
    color: var(--ink-2);
    background: none;
}

.answer-body :deep(table) {
    width: 100%;
    margin: 0 0 14px;
    border-collapse: collapse;
    font-size: 13px;
}

.answer-body :deep(th),
.answer-body :deep(td) {
    padding: 7px 10px;
    text-align: left;
    border: 1px solid var(--line-2);
}

/* ---------------- 响应式 ---------------- */

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

    .placeholder {
        padding: 44px 16px;
    }
}
</style>
