<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>PDF / Word / Markdown / TXT 上传解析</h3>
    <!-- el-upload 管理拖拽选择和文件列表；auto-upload=false 表示选中文件后不立即请求。 -->
    <el-upload v-model:file-list="fileList" class="document-upload" drag action="#"
      accept=".pdf,.docx,.md,.txt" :auto-upload="false" :limit="1" :disabled="busy"
      :on-change="chooseFile" :on-remove="removeFile" :on-exceed="exceedFile">
      <!-- 拖拽与点击使用同一选择流程，accept 只是浏览器提示，后端仍会校验。 -->
      <div class="el-upload__text">将文档拖到这里，或<em>点击选择文件</em></div>
      <!-- tip 插槽显示格式、大小和后续操作，避免把选中误认为已经上传。 -->
      <template #tip><div class="el-upload__tip">支持 PDF、DOCX、Markdown、TXT，每次 1 个，最大 5 MB。选择后点击“上传并解析”。</div></template>
    </el-upload>
    <!-- 文件通过 FormData 发送，不自己拼 multipart 边界。 -->
    <div class="row"><el-button class="upload-button" type="primary" :loading="busy" :disabled="busy || !file" @click="upload">上传并解析</el-button></div>
    <!-- 列表内容来自数据库，不是浏览器临时文件列表。 -->
    <div v-for="item in documents" :key="item.id" class="card">
      <!-- 点击读取原文详情，不在列表请求中重复下载所有正文。 -->
      <el-button link :disabled="busy" @click="view(item.id)">{{ item.originalName }}</el-button>
      <!-- 字符数表示文本量，不是 Token 数。 -->
      <span> {{ item.fileType }}，{{ item.characters }} 字符，切分：{{ item.chunked ? '完成' : '未完成' }}，向量化：{{ item.vectorized ? '完成' : '未完成' }}</span>
    </div>
    <!-- 原文按纯文本显示，Markdown 文件也不在这里执行 HTML。 -->
    <section v-if="detail"><h4>{{ detail.originalName }}</h4><pre class="parsed-content">{{ detail.content }}</pre></section>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 当前选择的本地文件，尚未上传时只存在于浏览器。
const file=ref(null)
// 已保存文档摘要。
const documents=ref([])
// 当前选中文档的解析原文。
const detail=ref(null)
// 上传、解析和读取期间禁用操作。
const busy=ref(false)
// 文件列表由 el-upload 展示；它与数据库里已经上传的 documents 列表不同。
const fileList=ref([])
// 输入组件包装后的 UploadFile，校验其 raw 原始 File；通过后保存供 FormData 使用。
function chooseFile(uploadFile) {
  // raw 才是浏览器 File，不能把带 name、status 等信息的包装对象直接发送给后端。
  const raw=uploadFile.raw
  // 扩展名统一转小写；文件格式最终仍以服务端实际解析结果为准。
  const extension=raw?.name.split('.').pop().toLowerCase()
  // auto-upload=false 时在 on-change 中校验，选中非法文件立即清空选择。
  if (!raw || !['pdf','docx','md','txt'].includes(extension) || raw.size===0 || raw.size>5*1024*1024) {
    // 清空业务文件与可见列表，避免按钮仍然引用上一个文件。
    file.value=null
    fileList.value=[]
    // 说明允许的格式和大小，用户可以重新选择。
    ElMessage.warning('请选择不超过5MB的非空PDF、DOCX、Markdown或TXT文件')
    return
  }
  // 此处只选择，不上传；点击按钮后才通过公共 request 发送。
  file.value=raw
}
// 无需返回值；移除待上传文件时同步清空业务变量，上传按钮随之禁用。
function removeFile() {
  // 只移除本地选择，不删除数据库文档或服务器文件。
  file.value=null
}
// 超出 limit=1 时提示先移除旧选择，不悄悄上传或替换另一个文件。
function exceedFile() {
  // 组件不会把超出的文件加入列表，当前选择保持不变。
  ElMessage.warning('每次上传一个文件，请先移除已选文件后重新选择')
}
// 无输入参数，刷新文档摘要列表。
async function loadDocuments() {
  // 普通 GET 使用统一 JSON 返回结构。
  const response=await request.get('/api/rag/documents')
  // 仅成功时替换已有列表。
  if (response.code==='200') documents.value=response.data
}
// 输入数据库编号，读取纯文本详情。
async function view(id) {
  // 公共封装负责错误提示。
  try {
    // 编号来自文档列表，不把用户文件路径作为接口路径。
    const response=await request.get(`/api/rag/documents/${id}`)
    // 正文按纯文本展示。
    if (response.code==='200') detail.value=response.data
  // 不重复提示公共请求错误。
  } catch { }
}
// 无输入参数，提交当前文件，成功后刷新记录并展示原文。
async function upload() {
  // 正在上传时不重复创建请求。
  if (busy.value) return
  // 后端会再次验证，页面提前拒绝明显无效选择。
  if (!file.value || file.value.size>5*1024*1024) return ElMessage.warning('请选择不超过5MB的文件')
  // 禁用重复提交。
  busy.value=true
  // 清除上次原文，避免误把旧内容当作新解析结果。
  detail.value=null
  // FormData 与后端的 file 字段对应。
  const body=new FormData()
  // 浏览器自动携带原始文件名和 multipart 边界。
  body.append('file',file.value)
  // 保存或解析失败仍要恢复操作。
  try {
    // 不手动设置 Content-Type，沿用脚手架对 FormData 的处理。
    const response=await request.post('/api/rag/documents/upload',body)
    // 成功后显示真实新增编号对应的内容。
    if (response.code==='200') { detail.value=response.data; await loadDocuments() }
  // 公共封装已提示错误。
  } catch {
  // 上传结束解除禁用。
  } finally { busy.value=false }
}
// 页面刷新后从数据库恢复列表，不恢复尚未上传的本地文件。
onMounted(async()=>{ try { await loadDocuments() } catch { } })
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

