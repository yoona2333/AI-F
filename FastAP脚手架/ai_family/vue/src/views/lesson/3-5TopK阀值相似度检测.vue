<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>TopK + 阈值相似度检索</h3>
    <!-- v-model 同步 question，textarea 显示三行，maxlength 限制字符数；busy 时禁用，后端仍会独立校验。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="1000" :disabled="busy" />
    <!-- 两个 v-model 分别绑定条数和分数；min/max 限制范围，step=0.05 只控制点击加减的步进，不是最优阈值。 -->
    <div class="row">TopK <el-input-number v-model="topK" :min="1" :max="10" :disabled="busy" />阈值 <el-input-number v-model="threshold" :min="-1" :max="1" :step="0.05" :disabled="busy" /></div>    <!-- 本节只检索，不生成答案。 -->
    <el-button class="run-button" type="primary" :loading="busy" :disabled="busy" @click="run">检索片段</el-button>
    <!-- 空结果不能用相似度最高但低于阈值的片段强行填充。 -->
    <p v-if="completed && !sources.length">没有达到条件的片段</p>
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
// 无输入参数，提交当前检索设置并显示来源。
async function run() {
  // 空白问题不调用 Embedding。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 清除上轮结果，避免新请求失败时误看旧证据。
  sources.value=[]
  // 标记本次未完成。
  completed.value=false
  // 禁用操作。
  busy.value=true
  // 公共封装负责异常提示。
  try {
    // 后端计算真实分数、过滤与排序。
    // 问题、条数和阈值三个键对应后端检索请求对象；分数由后台计算，前端不传来源或向量。
    const response=await request.post('/api/rag/search',{question:question.value,topK:topK.value,threshold:threshold.value})
    // 业务成功后即使空数组也要展示已完成状态。
    // 即使 data=[] 也是成功检索；同时标记 completed，模板才能显示“没有达到条件的片段”，而非一直像未发送。
    if (response.code==='200') { sources.value=response.data; completed.value=true }
  // 失败时不显示成功结果。
  } catch {
  // 解除等待。
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

