<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>RAG Prompt 与防止无依据回答</h3>
    <!-- v-model 同步 question，textarea 显示三行，maxlength 限制字符数；busy 时禁用，后端仍会独立校验。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="1000" :disabled="busy" />
    <!-- 两个 v-model 分别绑定条数和分数；min/max 限制范围，step=0.05 只控制点击加减的步进，不是最优阈值。 -->
    <div class="row">TopK <el-input-number v-model="topK" :min="1" :max="10" :disabled="busy" />阈值 <el-input-number v-model="threshold" :min="-1" :max="1" :step="0.05" :disabled="busy" /></div>    <!-- 同步等待检索与完整回答。 -->
    <el-button class="run-button" type="primary" :loading="busy" :disabled="busy" @click="run">根据资料回答</el-button>
    <!-- answer 非空才显示；renderMarkdown 生成的 HTML 交给 v-html，来源原文仍在下方独立按纯文本展示。 -->
    <div v-if="answer" class="card markdown-content" v-html="renderMarkdown(answer)"></div>
    <!-- prompt 有内容时才显示；details/summary 提供原生折叠区，展开可核查模型实际收到的用户消息。 -->
    <details v-if="prompt"><summary>本轮用户 Prompt</summary><pre>{{ prompt }}</pre></details>
    <!-- v-for 按命中顺序绘制卡片，key 使用片段主键，index 为从 0 开始的位置；来源直接来自后台检索。 -->
    <div v-for="(item,index) in sources" :key="item.id" class="card source-card">
      <!-- index+1 生成可读的 [1]、[2]，与后端 Prompt 使用同一顺序；item.chunkIndex 是文档内位置。 -->
      <strong>[{{ index+1 }}] {{ item.originalName }}，片段 {{ item.chunkIndex }}</strong>
      <!-- toFixed(6) 只把展示保留六位小数，不改变后端实际过滤值；item.id 是数据库片段主键。 -->
      <p>余弦：{{ item.score.toFixed(6) }}，片段编号：{{ item.id }}</p>
      <!-- 插值按纯文本输出来源，pre 保留换行；不把文档内容当作可执行 HTML。 -->
      <pre>{{ item.content }}</pre>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import { marked } from 'marked'

// 当前问题单独向量化；修改问题后再次提交会重新检索。
const question=ref('耳机拆封且影响二次销售，还能无理由退货吗？')
// 最多保留三条通过阈值的结果。
// 绑定 TopK 数字输入框，3 表示至多三条通过阈值的片段，不承诺一定命中三条。
const topK=ref(3)
// 演示起点不是通用最优阈值，需要看实际命中与答案。
// 绑定余弦阈值，0.3 只是本例起点；输入值送给后端过滤，不是 30% 的答案正确率。
const threshold=ref(0.3)
// 加载状态控制输入与重复提交。
const busy=ref(false)
// 本轮实际来源，初次没有预设结果。
// 保存本轮检索命中的来源，初始为空；开始新请求要清空，避免把上次依据错当成本次结果。
const sources=ref([])
// 已完成一次请求后才显示无命中提示。
// 初始 false 区分“尚未检索”与“检索成功但无结果”；本页模板使用此状态时才显示空命中提示。
const completed=ref(false)
// 本轮完整回答与实际 Prompt。
const answer=ref('')
// 只用于核对上下文，不包含 API Key。
const prompt=ref('')
// 输入回答原文，转义原始 HTML 后同步解析 Markdown。
function renderMarkdown(text) {
  // 原始标签只按文本显示，不作为模型提供的页面元素执行。
  // 空值先回退空字符串，再依次转义 &、<、>，让原始 HTML 标签按文字显示；数据库保存的原文不改。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // 保留常见标题、列表、代码和表格，普通换行交给 Markdown 处理。
  // 把文本转成供 v-html 使用的 HTML 字符串；gfm 启用表格等语法，breaks=false 不把普通换行强转为 br，async=false 同步返回。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// 无输入参数，检索后生成回答并显示实际来源。
async function run() {
  // 拒绝空白提问。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 禁用操作并清理旧证据。
  busy.value=true
  // 新请求不能沿用上轮回答。
  answer.value=''
  // 新请求不能沿用上轮 Prompt。
  prompt.value=''
  // 清理旧来源列表。
  sources.value=[]
  // 两个模型阶段需要更长等待，仅本次配置。
  try {
    // 问题和检索参数交给后端，前端不直接提交证据。
    // 后端先检索再生成，timeout=180000 为本次请求留出 180 秒；请求字段不包含页面伪造的证据。
    const response=await request.post('/api/rag/answer',{question:question.value,topK:topK.value,threshold:threshold.value},{timeout:180000})
    // 无命中时后端返回固定无依据提示，同样属于成功处理。
    // 同一响应中分别取完整回答、实际用户 Prompt 和真实来源，更新三个区域；固定无依据提示也属于正常处理。
    if (response.code==='200') { answer.value=response.data.answer; prompt.value=response.data.prompt; sources.value=response.data.sources }
  // 公共封装已提示。
  } catch {
  // 恢复操作。
  // finally 在成功、抛异常或 try 中提前 return 时都会执行，确保输入和按钮恢复，不让页面一直卡在等待。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* padding 留出四周阅读空隙，14px 为基础字号；min-width:0 允许内容在父布局中收缩，避免长字串撑宽页面。 */
.rag-page { padding: 20px; background: white; border-radius: 10px; font-size: 14px; min-width: 0; }
/* flex 让参数横排，gap 留出间距，align-items 垂直居中，flex-wrap 在小屏自动换行，margin 分隔上下区域。 */
.row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 12px 0; }
/* pre-wrap 保留来源的换行及空格，overflow-wrap:anywhere 允许长词折行，13px 等宽字便于核对原文。 */
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f4f6; padding: 12px; border-radius: 6px; font: 13px/1.7 Consolas, monospace; }
/* 每个片段与发言独立显示，方便核对来源。 */
.card { border: 1px solid #e5e7eb; padding: 12px; margin: 12px 0; border-radius: 8px; min-width: 0; }
/* 用户发言按纯文本保留换行。 */
.user-content { white-space: pre-wrap; }
/* Markdown 正文与第一章聊天字号一致。 */
.markdown-content { font-size: 14px; line-height: 1.7; overflow-wrap: anywhere; }
/* v-html 动态生成的 p 没有本组件的作用域属性，使用 :deep 才能命中，6px 上下边距避免段落过松。 */
.markdown-content :deep(p) { margin: 6px 0; }
/* 限制模型标题，避免对话里出现过大文字。 */
.markdown-content :deep(h1) { font-size: 20px; }
.markdown-content :deep(h2) { font-size: 18px; }
.markdown-content :deep(h3), .markdown-content :deep(h4), .markdown-content :deep(h5), .markdown-content :deep(h6) { font-size: 16px; }
/* 列表和代码块按 Markdown 本身排版。 */
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 24px; }
.markdown-content :deep(pre) { white-space: pre; overflow: auto; }
.markdown-content :deep(code) { font: 13px/1.7 Consolas, monospace; }
/* table 作为块限制在容器内，overflow-x:auto 让超宽表格横向滚动，border-collapse 合并相邻边框。 */
.markdown-content :deep(table) { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; }
.markdown-content :deep(th), .markdown-content :deep(td) { border: 1px solid #cbd5e1; padding: 6px 10px; }
/* 图片宽度不能超过消息。 */
.markdown-content :deep(img) { max-width: 100%; }
</style>

