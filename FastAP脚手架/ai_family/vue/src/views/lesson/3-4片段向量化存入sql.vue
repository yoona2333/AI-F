<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>片段向量化并存入 MySQL</h3>
    <!-- v-model 绑定数字 documentId；change 在选项改变后读取该文档片段，busy 时不允许切换。 -->
    <div class="row"><el-select v-model="documentId" :disabled="busy" @change="loadChunks">
      <!-- v-for 遍历文档摘要，key 用主键识别选项，label 展示文件名，value 把真实编号写入 documentId。 -->
      <el-option v-for="item in documents" :key="item.id" :label="item.originalName" :value="item.id" />
    </el-select></div>    <!-- 先在切分页完成片段，再处理当前选中文档。 -->
    <p>每批最多两条片段，全部保存成功后文档才标记为已向量化。</p>
    <!-- click 调用 run；loading 显示等待，disabled 在等待或没有 documentId 时禁止再次提交。 -->
    <el-button class="run-button" type="primary" :loading="busy" :disabled="busy || !documentId" @click="run">批量向量化并保存</el-button>
    <!-- 显示数据库实际保存的片段和处理信息。 -->
    <div v-for="item in items" :key="item.id" class="card chunk-card">
      <!-- 主键不同于文档内序号，重切会重新生成主键。 -->
      <strong>片段 {{ item.chunkIndex }}，编号 {{ item.id }}</strong>
      <!-- dimension 来自保存结果；|| 在模型名为空时显示“未向量化”，不在页面写死 256 冒充已保存。 -->
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

// 下拉框只存摘要，片段从独立接口读取。
// 响应式列表保存已上传文档摘要，初始没有选项；模板自动解包 ref，脚本中通过 .value 读写。
const documents=ref([])
// 当前文档编号，初次进入时选择列表第一篇。
// 下拉框保存数字主键，不是文件名；null 表示还没有文档可选，按钮据此禁用。
const documentId=ref(null)
// 当前文档的实际片段列表。
// 保存后端返回的片段列表，替换它会触发卡片重新渲染；编号、模型和维度来自数据库。
const items=ref([])
// 处理期间禁止切换文档和重复操作。
const busy=ref(true)
// 无输入参数，按当前文档编号读取片段列表。
async function loadChunks() {
  // 切换文档先清空旧片段，避免混淆来源。
  items.value=[]
  // 没有上传文档时不请求空编号。
  if (!documentId.value) return
  // 公共封装显示读取错误。
  try {
    // params 编码查询字符串，不手工拼接 SQL 条件。
    // 第二个参数 params 会编码为 ?documentId=当前编号；这是 HTTP 查询参数，不是 SQL，后端据编号取片段。
    const response=await request.get('/api/rag/chunks',{params:{documentId:documentId.value}})
    // 只有成功结果进入预览。
    // 统一响应 code 是字符串；成功的 data 才是片段数组，赋值会更新页面，不能用失败响应覆盖已有记录。
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
    // 选择第一篇已有文档，不预设某个编号。
    documents.value=response.data
    // 空列表时保持 null，提示先上传。
    // [0] 取第一项，?. 在没有该项时返回 undefined，|| null 回退为未选择；不用写死数据库自增编号。
    documentId.value=documents.value[0]?.id || null
    // 按真实编号加载列表。
    await loadChunks()
  // 公共封装已提示错误。
  } catch {
  // 所有路径都结束初始等待。
  // finally 在成功、抛异常或 try 中提前 return 时都会执行，确保输入和按钮恢复，不让页面一直卡在等待。
  } finally { busy.value=false }
}
// 初次进入与刷新都恢复数据库中的内容。
onMounted(restore)
// 无输入参数，读取当前 documentId，等待后台全部向量化结束后更新 items；不返回页面业务数据。
// 请求失败由公共封装提示，保留现有原文供查看，finally 恢复输入和按钮。
async function run() {
  // 进入等待，保留片段原文便于查看。
  busy.value=true
  // 公共封装提示模型或数据库错误。
  try {
    // 为多个批次设置更长 HTTP 等待时间，不修改公共 request。
    // 正文只传 documentId；第三个参数 timeout=300000 是本次浏览器请求最多等待 300 秒，不改变公共客户端或服务器模型超时。
    const response=await request.post('/api/rag/vectors',{documentId:documentId.value},{timeout:300000})
    // 结果中的维度和模型名来自数据库，不由页面预设。
    // 统一响应 code 是字符串；成功的 data 才是片段数组，赋值会更新页面，不能用失败响应覆盖已有记录。
    if (response.code==='200') items.value=response.data
  // 失败后可以重新对整篇执行，未完成状态不会用于检索。
  } catch {
  // 成功失败都恢复按钮。
  // finally 在成功、抛异常或 try 中提前 return 时都会执行，确保输入和按钮恢复，不让页面一直卡在等待。
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

