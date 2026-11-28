<template>
  <!-- messages保存已确认写入的问答，currentQuestion/draft保存本次临时内容，tools仅保存本轮真实工具记录。 -->
  <div class="agent-page">
    <!-- 标题对应聊天与工具执行记录。 -->
    <h3>MCP 商城智能客服</h3>
    <!-- v-for逐项读取messages；数据库历史用真实id，done后本地追加项用临时id，:key供Vue区分列表项。 -->
    <article v-for="item in messages" :key="item.id" class="message">
      <!-- 三元表达式按role显示发言者，user为用户，assistant为已保存客服回答；不是切换模型身份的设置。 -->
      <strong>{{ item.role === 'user' ? '用户' : '客服' }}</strong>
      <!-- v-if仅对assistant调用markdown；v-html把返回HTML插入div，支持段落、表格、列表及代码块，原content不变。 -->
      <div v-if="item.role === 'assistant'" class="markdown" v-html="markdown(item.content)"></div>
      <!-- 用户消息用插值显示原文，CSS保留其换行，不解析用户输入中的Markdown。 -->
      <p v-else>{{ item.content }}</p>
    </article>
    <!-- currentQuestion非空时才显示本次临时区；done把问答追加到messages并清空它，该区随v-if移除。 -->
    <article v-if="currentQuestion" class="message">
      <!-- currentQuestion是发送时复制的question原文，插值按纯文本显示，不随输入框后续清空而丢失。 -->
      <strong>本次问题</strong><p>{{ currentQuestion }}</p>
      <!-- busy为true时流仍在执行，显示正在生成；缺少done而结束时保留草稿并显示本次未完成。 -->
      <strong>{{ busy ? '正在生成' : '本次未完成' }}</strong>
      <!-- 每次delta更新draft都会重新解析当前轮全文，未闭合的Markdown会随后续文字到达重新排版。 -->
      <div class="markdown" v-html="markdown(draft)"></div>
    </article>
    <!-- tools每项来自本轮MCP调用的tool事件，:key使用后端执行id；同名工具多次调用也分别显示，不按工具名合并。 -->
    <el-card v-for="item in tools" :key="item.id" class="tool-step" shadow="never">
      <!-- #header为卡片标题插槽，三元表达式将started/completed/failed映射为执行中/完成/失败。 -->
      <!-- durationMs单位为毫秒，仅结束事件携带；!= null排除null和undefined，但保留0毫秒的正常显示。 -->
      <template #header>{{ item.toolName }} · {{ item.status === 'started' ? '执行中' : item.status === 'completed' ? '完成' : '失败' }} <span v-if="item.durationMs != null">· {{ item.durationMs }} ms</span></template>
      <!-- arguments是开始事件中的参数对象；JSON.stringify第二项null保留字段，第三项2设置两空格缩进，插值按文本显示。 -->
      <pre>参数：{{ JSON.stringify(item.arguments,null,2) }}</pre>
      <!-- v-if仅在completed后展示实际观察result，执行中或失败时不显示一份空的成功结果；pre保留原始换行。 -->
      <pre v-if="item.status === 'completed'">结果：{{ item.result }}</pre>
    </el-card>
    <!-- v-model与question双向绑定，模板自动解包ref；textarea为多行输入，rows=3设置初始高度，maxlength=2000对应请求上限。 -->
    <!-- busy或loading为true时禁用输入，避免问答流或历史读取过程中更改本次条件，后端仍有独立校验。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="2000" :disabled="busy || loading" />
    <!-- 发送点击调用send；busy/loading表示当前有任务，!ready表示历史尚未确认，任一为true都禁用按钮。 -->
    <!-- :loading仅绑定busy，显示本次问答等待；type=primary使用主题色突出发送操作。 -->
    <el-button type="primary" :disabled="busy || loading || !ready" :loading="busy" @click="send">发送</el-button>
    <!-- 重新读取调用load恢复数据库实际记录，loading显示读取等待；busy或loading期间禁用，避免请求交叉更新。 -->
    <el-button :disabled="busy || loading" :loading="loading" @click="load">重新读取历史</el-button>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'
import { streamRequest } from '@/utils/stream'

// ref保存当前输入字符串，模板v-model自动解包，脚本用question.value读取；POST仅提交该原文，历史由后端查库。
const question=ref('帮我查订单 DEMO1001 的状态和物流。')
// messages初始为空数组，GET成功时整体替换；done到达后追加本次user/assistant两项，字段均为id、role、content。
const messages=ref([])
// busy从发送前true到流结束finally恢复false，控制表单禁用、加载图标和临时区状态文字。
const busy=ref(false)
// loading表示GET历史正在等待，防止重复读取，并与busy共同控制输入和按钮。
const loading=ref(false)
// ready表示已确认当前数据库历史；首次加载前及问答未确认完成后为false，重新读取成功才恢复true。
const ready=ref(false)
// currentQuestion固定本次发送的原问题，非空时显示临时区；成功done或历史恢复后清空。
const currentQuestion=ref('')
// draft仅累加当前模型生成批次的文字增量，Markdown只在显示时转换，尚未作为已保存答案。
const draft=ref('')
// tools每项初始含id/status/toolName/arguments，结束事件再补result/durationMs；新发送前清空，仅属于本次执行。
const tools=ref([])

// Markdown显示函数：text是客服回答或流式草稿原文，返回HTML字符串给v-html；不请求模型，不修改原文或数据库。
function markdown(text) {
  // (text || '')使空值按空串显示；replace依次转义&、<、>，正则/g处理所有出现位置，使原始HTML标签按文字显示。
  // 先处理&，防止后面生成的&lt;和&gt;再次被转义；转换不负责判断回答事实是否正确。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // marked.parse将转义后的全文解析为HTML；gfm=true启用表格等语法，breaks=false不把普通单换行强制变成br。
  // async=false保证直接返回字符串而非Promise，模板在每次draft变化后可同步重绘当前草稿。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}

// 历史恢复函数：无形参，GET读取全部已保存问答，成功后替换messages并设置ready，清除上次临时内容。
// 不返回业务对象；已有任务时立即返回，网络或业务错误由公共request提示，finally恢复loading供再次读取。
async function load() {
  // ||表示任一任务进行中即return，避免历史响应覆盖正在生成的消息，也避免两个GET交叉返回。
  if (busy.value || loading.value) return
  // loading先设true锁定操作，ready设false使发送保持禁用；只有下方成功分支能确认本次历史。
  loading.value=true
  ready.value=false
  // 请求与状态复原分别处理，数据库错误由公共request显示。
  try {
    // request.get返回公共封装解包后的业务响应对象，不是原始AxiosResponse；此接口只查数据库，不执行Agent。
    const response=await request.get('/api/mcp/agent/messages')
    // 严格匹配字符串业务码200；HTTP返回不代表业务成功，非200时不覆盖已有显示或设置ready。
    if (response.code==='200') {
      // response.data是id/role/content数组，整体赋给ref触发历史列表更新，空数组表示当前无已保存消息。
      messages.value=response.data
      // 历史已确认，GET结束且loading恢复后可以发送本轮追问。
      ready.value=true
      // 历史恢复后移除上次临时问题和草稿，避免同一内容重复显示。
      currentQuestion.value=''
      // 草稿来自上次未确认执行；恢复数据库真实内容后移除它，避免与保存的答案重复。
      draft.value=''
    }
  // 公共封装已经提示错误，保留现有显示等待重新读取。
  } catch {
  // 成功或失败都允许再次点击历史读取。
  } finally { loading.value=false }
}

// 发送函数：无形参，读取输入快照，通过POST消费事件流；tool更新卡片，delta更新草稿，done追加最终问答。
// 不返回业务对象；缺少done按未完成处理，保留过程并要求重新读取历史，所有连接退出路径都在finally恢复busy。
async function send() {
  // 三个条件用||连接，已有问答、正在读历史或尚未确认历史时，任意一个成立都不创建第二条事件流。
  if (busy.value || loading.value || !ready.value) return
  // trim只判断全空白，warning提示后return；不改变接下来复制和发送的原文，后端仍校验空白与长度。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 将当前输入复制到本次问题快照，后续发送和done追加都读取同一原文。
  currentQuestion.value=question.value
  // 清空上一轮草稿，不把不同问题的模型文字连在一起。
  draft.value=''
  // 新建本次工具数组，时间线不会从历史答案中推测或恢复。
  tools.value=[]
  // 接下来直到finally都禁止输入和重复发送。
  busy.value=true
  // finished是本次send调用内的局部变量，初始false，仅收到业务done才设true；网络结束和工具completed都不设置它。
  let finished=false
  // modelStep保存后端delta.step生成批次标识，初始null；标识变化时清空前一批文字，避免多轮回答直接拼接。
  let modelStep=null
  // failure保存error事件中的message，流结束且没有done时优先显示它，空串则使用通用未完成提示。
  let failure=''
  // streamRequest处理POST、中文解码、SSE分帧与普通网络错误。
  try {
    // 仅提交问题，客户端不提交历史、模型参数或工具执行结果。
    await streamRequest('/api/mcp/agent/stream',{
      // data是POST的JSON正文，仅含question快照；服务端自行读取历史并选择工具，客户端不提供执行结果。
      data:{question:currentQuestion.value},
      // 每收到一个完整SSE帧，公共工具先解析JSON再调用此回调；解构参数取得event名称与data负载字典。
      // 回调不返回业务结果，通过闭包更新messages/draft/tools以及本次局部finished/modelStep/failure。
      onEvent:({event,data})=>{
        // 模型可能在不同轮次输出文字，切换step时重新显示当前轮草稿。
        if (event==='delta') {
          // !==比较后端标识与已显示批次；不同则先记录新标识，再清空旧草稿，本次data.text随后仍会被追加。
          if (modelStep!==data.step) { modelStep=data.step; draft.value='' }
          // +=只拼接新增text，不用其覆盖已有本轮全文；draft变化触发模板markdown(draft)重新渲染，尚未写入历史列表。
          draft.value+=data.text
        }
        // event为tool且status为started才追加卡片；{...data}展开复制id/status/toolName/arguments，不预填结果或耗时。
        if (event==='tool' && data.status==='started') tools.value.push({...data})
        // 完成或失败事件只能更新已有同id记录，不按名称猜测。
        if (event==='tool' && data.status!=='started') {
          // find从tools寻找id严格相等的一项，返回响应式原对象，未找到为undefined；同名工具不能仅按name匹配。
          const item=tools.value.find(item=>item.id===data.id)
          // Object.assign将data中的status/result/durationMs合入原项，保留开始时的名称和参数；无匹配项则不补造卡片。
          if (item) Object.assign(item,data)
        }
        // done说明最终消息已校验且两次保存已返回，正文以此完整答案为准。
        if (event==='done') {
          // Date.now返回当前毫秒时间戳，模板字符串加local-前缀形成本地key；这不是数据库主键，刷新后GET会取得真实id。
          const localId=`local-${Date.now()}`
          // push一次追加两个对象：先user问题快照，再assistant最终answer；-user/-assistant后缀区分同轮两个列表key。
          // role用于显示发言者及决定是否Markdown渲染，content保留正文原文；data.answer替代临时draft作为正式答案。
          messages.value.push({id:localId+'-user',role:'user',content:currentQuestion.value},{id:localId+'-assistant',role:'assistant',content:data.answer})
          // 清除临时区和输入，避免最终答案重复展示。
          currentQuestion.value=''
          // 正式答案已进入messages，清空草稿防止重复显示。
          draft.value=''
          // 清空输入供下一轮追问；历史仍由messages展示。
          question.value=''
          // 只有这个事件把本次标为成功，completed工具事件不会设置它。
          finished=true
        }
        // error负载的message是服务端统一失败提示；仅记录到failure，不追加到正文，也不设置finished。
        if (event==='error') failure=data.message
      }
    })
    // await返回只表示连接读取结束；!finished说明未收到done，用failure || 默认提示选择非空错误，保留现有过程。
    if (!finished) ElMessage.error(failure || '连接已结束，但本次问答未完整完成，请重新读取历史')
  // 网络和普通JSON错误由公共streamRequest提示。
  } catch {
  // 无论连接如何结束，都解除busy；失败时先重新读取数据库再继续。
  } finally {
    // 没有done的执行中工具标失败，已有完成记录不覆盖。
    if (!finished) {
      // 数据库可能已保存部分或完整问答，重新读取后才能确定当前历史。
      ready.value=false
      // forEach逐项检查当前数组，只把started改failed；已completed的观察与耗时保持，未结束项也不补造结果或时长。
      tools.value.forEach(item=>{ if (item.status==='started') item.status='failed' })
    }
    // 允许重新读取历史，成功时也允许继续追问。
    busy.value=false
  }
}

// onMounted注册load函数引用，组件挂载后由Vue调用一次；不是在此处写load()立即执行，成功读取后发送才可启用。
onMounted(load)
</script>
<style scoped>
/* 白底与14px正文统一阅读，min-width允许长工具输出在父容器内收缩。 */
.agent-page { padding:20px; background:white; border-radius:10px; font-size:14px; min-width:0; }
/* 历史、当前问题与工具卡片留出上下间距。 */
.message,.tool-step { margin-bottom:12px; }
/* 聊天和JSON保留换行，长编号也能折行。 */
p,pre { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.7; }
/* 回答按Markdown标签排版，长词折行，宽表格在回答区域内横向滚动。 */
.markdown { overflow-wrap:anywhere; line-height:1.7; overflow-x:auto; }
/* v-html生成的段落需用deep匹配；normal覆盖普通消息p的pre-wrap，段落间距由标签控制。 */
.markdown :deep(p) { white-space:normal; margin:6px 0; }
/* 一级标题限制为20px，保持与聊天正文的阅读比例。 */
.markdown :deep(h1) { font-size:20px; }
/* 二级标题使用18px，与一级形成层次。 */
.markdown :deep(h2) { font-size:18px; }
/* 三至六级标题统一16px，正文继承页面14px。 */
.markdown :deep(h3),.markdown :deep(h4),.markdown :deep(h5),.markdown :deep(h6) { font-size:16px; }
/* 列表左侧保留24px，使项目符号与序号位于回答区域内。 */
.markdown :deep(ul),.markdown :deep(ol) { padding-left:24px; }
/* 表格合并相邻边框，上下留出间距，方便阅读商品对比。 */
.markdown :deep(table) { border-collapse:collapse; margin:10px 0; }
/* 表头与普通单元格采用同样的边框和内边距，使各字段清楚分列。 */
.markdown :deep(th),.markdown :deep(td) { border:1px solid #dcdfe6; padding:6px 10px; }
/* Markdown代码块保留缩进和长行，内容超过宽度时在块内滚动。 */
.markdown :deep(pre) { white-space:pre; overflow:auto; padding:12px; background:#f3f4f6; }
/* 行内代码与代码块内容统一使用13px等宽字体和1.7行高。 */
.markdown :deep(code) { font:13px/1.7 Consolas,monospace; }
/* 工具参数以等宽字体显示，便于核对字段与嵌套结构。 */
pre { padding:12px; background:#f3f4f6; font:13px/1.7 Consolas,monospace; }
/* 输入与发送按钮分开，避免操作紧贴文本框。 */
.el-button { margin-top:12px; }
</style>

