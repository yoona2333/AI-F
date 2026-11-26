<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>按长度切分与重叠窗口</h3>
    <!-- 文档编号由摘要列表提供，正文仍由后端从数据库读取。 -->
    <div class="row"><el-select v-model="documentId" :disabled="busy" @change="loadChunks">
      <!-- value 使用数字编号，不能把文件名当成 documentId。 -->
      <el-option v-for="item in documents" :key="item.id" :label="item.originalName" :value="item.id" />
    </el-select></div>    <!-- 两个参数按字符计数，不是 Token。 -->
    <div class="row">长度 <el-input-number v-model="chunkSize" :min="100" :max="1000" :disabled="busy" />重叠 <el-input-number v-model="overlap" :min="0" :max="300" :disabled="busy" /></div>
    <!-- 重切会删除该文档旧片段和向量，操作前在页面说明。 -->
    <p>重新切分会替换该文档旧片段和旧向量，需要重新向量化。</p>
    <!-- 没有文档时不能切分。 -->
    <el-button class="run-button" type="primary" :loading="busy" :disabled="busy || !documentId" @click="run">切分并保存</el-button>
    <!-- 显示数据库实际保存的片段和处理信息。 -->
    <div v-for="item in items" :key="item.id" class="card chunk-card">
      <!-- 主键不同于文档内序号，重切会重新生成主键。 -->
      <strong>片段 {{ item.chunkIndex }}，编号 {{ item.id }}</strong>
      <!-- 维度为零表示还未保存向量，模型名用于检查配置。 -->
      <p>维度：{{ item.dimension }}，模型：{{ item.embeddingModel || '未向量化' }}</p>
      <!-- 原文以文本方式预览，不把文件内容当 HTML。 -->
      <pre>{{ item.content }}</pre>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// ref([]) 创建响应式文档列表，保存编号和名称，供 el-select 生成选项；初始为空数组。
const documents=ref([])
// 保存下拉框当前选中的数字主键；null 表示未选择。模板自动解包 ref，脚本通过 .value 读写。
const documentId=ref(null)
// 保存接口返回的片段数组，赋值后模板 v-for 会更新；不在前端自己计算或伪造片段。
const items=ref([])
// 初始 true 表示正在恢复数据；模板用它禁用操作，restore 的 finally 会恢复 false。
const busy=ref(true)
// 无输入参数，按当前文档编号读取片段列表。
async function loadChunks() {
  // 切换文档先清空旧片段，避免混淆来源。
  items.value=[]
  // 没有上传文档时不请求空编号。
  if (!documentId.value) return
  // 公共封装显示读取错误。
  try {
    // params 是 HTTP 查询参数，会编码为 /api/rag/chunks?documentId=当前编号，不是 SQL 条件。
    // .value 读取当前选中值，后台据此只查询该文档的片段。
    const response=await request.get('/api/rag/chunks',{params:{documentId:documentId.value}})
    // code 是统一响应中的字符串状态码；data 是片段数组，赋给 items 后页面自动刷新预览。
    if (response.code==='200') items.value=response.data
  // 读取失败保持空列表。
  } catch { }
}
// 无输入参数，进入页面时先加载文档，再加载其片段。
async function restore() {
  // 初次等待也要在结束时解除禁用。
  try {
    // 摘要接口从已上传文档恢复数据。
    const response=await request.get('/api/rag/documents')
    // 业务失败时不继续读取片段。
    if (response.code!=='200') return
    // 保存接口返回的全部摘要，供下拉框展示文件名，并以实际数据库主键作为选项值。
    documents.value=response.data
    // [0] 取第一篇；?. 在数组为空时得到 undefined，|| null 将它转为“未选择”，避免访问不存在的 id。
    documentId.value=documents.value[0]?.id || null
    // 等第一篇文档的片段读取完成后才解锁页面；没有文档时 loadChunks 直接返回。
    await loadChunks()
  // 公共封装已提示错误。
  } catch {
  // 所有路径都结束初始等待。
  } finally { busy.value=false }
}
// 把 restore 函数注册为挂载后的操作；这里传函数本身，不写 restore() 让它立即执行。
onMounted(restore)
// 默认窗口方便观察同一条件在切口附近的重复。
const chunkSize=ref(350)
// 绑定第二个数字输入框，默认重复 50 字；与长度 350 配合，后端每次将起点前进 300 字。
const overlap=ref(50)
// 无输入参数，对当前文档重新切分。
async function run() {
  // 保证窗口步长为正，后端也会再次检查。
  if (overlap.value>=chunkSize.value) return ElMessage.warning('重叠必须小于片段长度')
  // 开始处理，禁止切换文档。
  busy.value=true
  // 不把旧片段当成新切分结果。
  items.value=[]
  // 公共封装负责错误提示。
  try {
    // POST 第二个参数是 JSON 正文，三个键对应 RagChunkRequest；原文由后台按编号查询。
    // await 等完整结果，不是流式返回。
    const response=await request.post('/api/rag/chunks',{documentId:documentId.value,chunkSize:chunkSize.value,overlap:overlap.value})
    // data 是保存后重新查询的有序列表；用它替换 items，展示实际片段主键和内容。
    if (response.code==='200') items.value=response.data
  // 失败时不显示旧成功列表。
  } catch {
  // 结束加载。
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

