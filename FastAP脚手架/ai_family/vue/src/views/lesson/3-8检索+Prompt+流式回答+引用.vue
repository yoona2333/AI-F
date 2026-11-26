<template>
  <!-- 本节只展示当前技术链路，数据来自真实接口。 -->
  <div class="rag-page">
    <!-- 页面标题由课节名称对应。 -->
    <h3>检索 + Prompt + 流式回答 + 引用</h3>
    <!-- partial 保存本次收到的全部增量，生成结束后仍保留显示，下一次提交才清空。 -->
    <div v-if="partial" class="card markdown-content partial" v-html="renderMarkdown(partial)"></div>
    <!-- v-model 同步 question，textarea 显示三行，maxlength 限制字符数；busy 时禁用，后端仍会独立校验。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="1000" :disabled="busy" />
    <!-- 两个 v-model 分别绑定条数和分数；min/max 限制范围，step=0.05 只控制点击加减的步进，不是最优阈值。 -->
    <div class="row">TopK <el-input-number v-model="topK" :min="1" :max="10" :disabled="busy" />阈值 <el-input-number v-model="threshold" :min="-1" :max="1" :step="0.05" :disabled="busy" /></div>    <!-- 生成期间禁用发送，等待 done 表示本次回答完整结束。 -->
    <el-button class="run-button" type="primary" :loading="busy" :disabled="busy" @click="send">发送</el-button>
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
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { streamRequest } from '@/utils/stream'

// 当前问题单独向量化；修改问题后再次提交会重新检索。
const question=ref('耳机拆封且影响二次销售，还能无理由退货吗？')
// 最多保留三条通过阈值的结果。
// 绑定 TopK 数字输入框，3 表示至多三条通过阈值的片段，不承诺一定命中三条。
const topK=ref(3)
// 演示起点不是通用最优阈值，需要看实际命中与答案。
// 绑定余弦阈值，0.3 只是本例起点；输入值送给后端过滤，不是 30% 的答案正确率。
const threshold=ref(0.3)
// 初始 false 允许直接提问；发送后变 true，finally 恢复，控制输入和重复提交。
const busy=ref(false)
// 本轮实际来源，初次没有预设结果。
// 保存本轮检索命中的来源，初始为空；开始新请求要清空，避免把上次依据错当成本次结果。
const sources=ref([])
// 本次流式正文，开始新请求时清空，完成后保留供查看。
// 每个 delta 追加到此字符串，模板按 Markdown 渲染；刷新页面会重新初始化为空字符串。
const partial=ref('')
// 输入回答原文，转义原始 HTML 后同步解析 Markdown。
function renderMarkdown(text) {
  // 原始标签只按文本显示，不作为模型提供的页面元素执行。
  // 空值先回退空字符串，再依次转义 &、<、>，让原始 HTML 标签按文字显示；不会修改检索片段的原始文本。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // 保留常见标题、列表、代码和表格，普通换行交给 Markdown 处理。
  // 把文本转成供 v-html 使用的 HTML 字符串；gfm 启用表格等语法，breaks=false 不把普通换行强转为 br，async=false 同步返回。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// 无输入参数，提交当前问题并消费来源、正文、完成和错误事件。
async function send() {
  // 正在生成时不重复提交。
  if (busy.value) return
  // 没有问题就不检索。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 禁用输入和参数。
  busy.value=true
  // 本轮开始先清空旧增量。
  partial.value=''
  // 旧检索结果不能作为本轮来源。
  sources.value=[]
  // done 是业务完成标记，不是网络读取结束。
  // 仅收到业务 done 才变 true；网络流结束不等于回答完整。
  let finished=false
  // 服务端 error 事件提供具体业务提示。
  // 暂存服务端 error 事件的提示；流结束时若没 done，优先显示这个原因并保留临时正文。
  let streamError=''
  // 公共流式工具处理分帧、中文跨块和普通 JSON 错误。
  try {
    // 使用脚手架 streamRequest，不另写一套 SSE 分帧器。
    // 复用脚手架的 POST SSE 客户端，负责读取网络块、拼完整事件和 JSON 解码；await 等流结束，再检查业务完成信号。
    await streamRequest('/api/rag/chat/stream',{
      // POST 请求只发送当前问题与检索设置。
      // data 是请求 JSON 正文，不是 SSE 响应数据；后端使用同名 question/topK/threshold 校验并检索。
      data:{question:question.value,topK:topK.value,threshold:threshold.value},
      // 输入已解析事件名和 JSON 数据，更新本轮页面状态。
      // 这是每收到一帧就调用的箭头函数；解构取出已解析的事件名 event 和 JSON 对象 data，不在这里手动切网络字符串。
      onEvent:({event,data})=>{
        // 正文完整输出后才收到来源事件，内容来自实际检索，不是模型猜测。
        // 来源事件携带 sources 数组，替换本轮卡片；它由实际检索产生，不从回答中的文件名反推。
        if (event==='sources') sources.value=data.sources
        // 增量直接追加，Markdown 随文字更新。
        // += 只追加本次新增文字；ref 更新后 Markdown 随之重算，不能用赋值覆盖导致只剩最后一块。
        if (event==='delta') partial.value+=data.content
        // 只有正文完整性检查通过后的 done 才确认完成。
        // 后端在正文检查和来源发送完成后才发送 done，设置本轮成功标志；不要在 sources 或第一个 delta 到达时就清空问题。
        if (event==='done') finished=true
        // 暂存错误，连接结束后显示，不把错误当成成功。
        // 记录提示而不是当作正文追加；后续没有 done 时保留输入和已收到文字，供用户核对。
        if (event==='error') streamError=data.message
      }
    })
    // 网络结束但没有 done，仍属于未完整完成。
    // 流关闭却没收到 done 仍视为未完成；return 结束本次发送，但 finally 仍会执行并解除 busy。
    if (!finished) return ElMessage.error(streamError || '回答未完成，请重新提问')
    // 回答成功后保留 partial 与 sources 供查看，只清空输入框，便于提出下一个完整问题。
    question.value=''
  // 公共流式工具已经提示网络或普通 JSON 错误。
  } catch {
  // 失败时保留已收到的增量并恢复操作。
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

