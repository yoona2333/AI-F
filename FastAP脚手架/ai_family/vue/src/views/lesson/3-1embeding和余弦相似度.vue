<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>Embedding 与余弦相似度</h3>
    <!-- 两段文本分别输入，同步等待真实 Embedding 结果。 -->
    <el-input v-model="firstText" type="textarea" :rows="3" :disabled="busy" />
    <!-- 第二段可改成无关文本，用实际分数对比。 -->
    <div class="row"><el-input v-model="secondText" type="textarea" :rows="3" :disabled="busy" /></div>
    <!-- 生成期间禁用，避免重复请求。 -->
    <el-button class="run-button" type="primary" :loading="busy" :disabled="busy" @click="compare">比较相似度</el-button>
    <!-- 只在本轮成功后展示，不用固定演示分数。 -->
    <section v-if="result" class="result">
      <!-- 分数不是百分比或正确率。 -->
      <p>模型：{{ result.model }}，维度：{{ result.dimension }}，余弦：{{ result.score.toFixed(6) }}</p>
      <!-- 默认预览八项，完整向量可展开。 -->
      <pre>第一段前8项：{{ result.firstVector.slice(0,8) }}
第二段前8项：{{ result.secondVector.slice(0,8) }}</pre>
      <!-- 完整数值用于观察，不要求人工解读某一维含义。 -->
      <details><summary>完整向量</summary><pre>{{ JSON.stringify(result,null,2) }}</pre></details>
    </section>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 两段初始文本含义相近，用户可以替换其中一段。
const firstText=ref('耳机拆封后还能无理由退货吗？')
// 同义但措辞不同，不用相同文字假装语义检索。
const secondText=ref('商品开封以后能不能申请七天退货？')
// 本轮返回值，刷新清空。
const result=ref(null)
// 控制输入与加载状态。
const busy=ref(false)
// 无输入参数，将两段当前文本提交到后端，更新本次结果。
async function compare() {
  // 不提交空白内容。
  if (!firstText.value.trim() || !secondText.value.trim()) return ElMessage.warning('请输入两段文本')
  // 开始加载，清除上轮分数。
  busy.value=true
  // 本轮失败时不能残留旧成功结果。
  result.value=null
  // 接口失败由公共封装提示。
  try {
    // 使用真实模型接口，不让前端计算一个预设分数。
    const response=await request.post('/api/rag/embedding/compare',{firstText:firstText.value,secondText:secondText.value})
    // 仅业务成功才更新结果。
    if (response.code==='200') result.value=response.data
  // 公共封装已显示错误。
  } catch {
  // 成功与失败均解除等待。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* 页面使用统一白底和阅读字号，长内容不撑开父容器。 */
.rag-page { padding: 20px; background: white; border-radius: 10px; font-size: 14px; min-width: 0; }
/* 各区域留出间距，按钮、输入框不挤在一起。 */
.row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 12px 0; }
/* 原文和工具数据保留换行，长行在区域内部折行。 */
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f4f6; padding: 12px; border-radius: 6px; font: 13px/1.7 Consolas, monospace; }
/* 每个片段与发言独立显示，方便核对来源。 */
.card { border: 1px solid #e5e7eb; padding: 12px; margin: 12px 0; border-radius: 8px; min-width: 0; }
/* 用户发言按纯文本保留换行。 */
.user-content { white-space: pre-wrap; }
/* Markdown 正文与第一章聊天字号一致。 */
.markdown-content { font-size: 14px; line-height: 1.7; overflow-wrap: anywhere; }
/* v-html 内元素通过 deep 接收作用域样式。 */
.markdown-content :deep(p) { margin: 6px 0; }
/* 限制模型标题，避免对话里出现过大文字。 */
.markdown-content :deep(h1) { font-size: 20px; }
.markdown-content :deep(h2) { font-size: 18px; }
.markdown-content :deep(h3), .markdown-content :deep(h4), .markdown-content :deep(h5), .markdown-content :deep(h6) { font-size: 16px; }
/* 列表和代码块按 Markdown 本身排版。 */
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 24px; }
.markdown-content :deep(pre) { white-space: pre; overflow: auto; }
.markdown-content :deep(code) { font: 13px/1.7 Consolas, monospace; }
/* 超宽表格在自身内部滚动。 */
.markdown-content :deep(table) { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; }
.markdown-content :deep(th), .markdown-content :deep(td) { border: 1px solid #cbd5e1; padding: 6px 10px; }
/* 图片宽度不能超过消息。 */
.markdown-content :deep(img) { max-width: 100%; }
</style>

