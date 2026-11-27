<template>
  <!-- 页面只提交本次商品资料，生成阶段和结果由服务端真实工作流决定。 -->
  <div class="workflow-page">
    <!-- 标题对应当前课节示例，表单输入和结果都采用统一阅读字号。 -->
    <h3>商品文案生产线</h3>
    <!-- v-model 双向绑定 product，textarea 使用多行输入，rows=4 为初始高度，maxlength=3000 对应资料长度上限。 -->
    <!-- busy 为 true 时 disabled 锁住本次条件，防止执行中修改表单；接口仍必须独立校验，前端限制不能代替后端。 -->
    <el-input v-model="product" type="textarea" :rows="4" :maxlength="3000" :disabled="busy" />
    <!-- channel保存固定路由键，label显示中文；busy期间禁止改动本次请求条件。 -->
    <el-select v-model="channel" :disabled="busy" class="channel-select">
      <!-- value与后端渠道枚举一致，不把中文标签作为节点名传入。 -->
      <el-option label="小红书" value="xiaohongshu" />
      <!-- 三个渠道互斥，当前请求只选其中一个。 -->
      <el-option label="抖音" value="douyin" />
      <!-- 公众号也使用稳定的路由键。 -->
      <el-option label="公众号" value="wechat" />
    </el-select>
    <!-- 点击才调用 run；loading 显示等待，disabled 禁止重复点击，二者读取 busy；开始前设 true，结束后 finally 复原。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="run">开始生成</el-button>
    <!-- 收到真实started事件才增加步骤，收到completed才改完成，不用定时器模拟执行。 -->
    <el-steps v-if="steps.length" direction="vertical" class="steps">
      <!-- 循环可能多次执行evaluate，使用事件顺序索引标识每一次，避免同名节点覆盖上一轮。 -->
      <el-step v-for="(item,index) in steps" :key="index" :title="labels[item.node] || item.node" :status="item.status" />
    </el-steps>
    <!-- 展开可核对已完成阶段的真实产出；候选阶段在内部执行三路并行后统一返回。 -->
    <details v-for="(item,index) in steps" :key="index" class="step-output">
      <!-- 结果仅在completed事件后出现，执行中不能填入固定成功内容。 -->
      <summary>{{ labels[item.node] || item.node }}：{{ item.status === 'finish' ? '完成' : item.status === 'error' ? '失败' : '执行中' }}</summary>
      <!-- 插值按纯文本显示JSON，不执行返回结果中的HTML。 -->
      <pre v-if="item.output">{{ JSON.stringify(item.output,null,2) }}</pre>
    </details>
    <!-- 成功拿到本轮完整状态后才展示最终结果，异常不保留上一轮的成功内容。 -->
    <section v-if="result" class="result">
      <!-- 卖点与原始资料分开，便于判断模型有没有添加用户未给出的事实。 -->
      <h4>提取卖点</h4>
      <!-- Markdown只影响显示，state中的原始字符串不被修改。 -->
      <div class="markdown" v-html="markdown(result.points)"></div>
      <!-- 并行分支分别写candidateA/B/C，按固定标签排三栏，不依赖它们的完成先后。 -->
      <div class="candidates">
        <!-- v-for 逐一取固定 A/B/C 标签，key 标识卡片；这里只按标签展示结果，真正生成是否并行由后端图负责。 -->
        <el-card v-for="letter in ['A','B','C']" :key="letter" shadow="never">
          <!-- 标签与模型评选时看到的A/B/C一致，不能用数组位置猜推荐版本。 -->
          <template #header>版本 {{ letter }} <el-tag v-if="result.winner === letter" type="success">推荐</el-tag></template>
          <!-- letter 为 A/B/C，动态拼键例如 candidate+B 得 candidateB，读取对应全文后再转 Markdown；不根据完成顺序猜推荐。 -->
          <div class="markdown" v-html="markdown(result['candidate'+letter])"></div>
        </el-card>
      </div>
      <!-- 推荐理由是模型判断，不宣称该版本已验证更高转化率。 -->
      <p>推荐理由：{{ result.recommendation }}</p>
      <!-- 显示每次真正被评分的版本，不把优化前的分数套到下一版。 -->
      <el-card v-for="item in result.versions" :key="item.round" shadow="never" class="version">
        <!-- round是已评估版本数，不是模型请求次数；第1版也需要评分。 -->
        <template #header>第 {{ item.round }} 版 · {{ item.score }} 分</template>
        <!-- 快照来自本次State，只在当前页面展示，不读取历史任务记录。 -->
        <div class="markdown" v-html="markdown(item.copy)"></div>
        <!-- 具体反馈是下一次优化的依据，而非只显示一个无从修改的分数。 -->
        <p>建议：{{ item.feedback }}</p>
      </el-card>
      <!-- 用最终 score 判断是否达到80；低分也返回正常最终状态，是因第三版用尽，必须显示未达标而非“优化通过”。 -->
      <el-tag :type="result.score >= 80 ? 'success' : 'warning'">{{ result.score >= 80 ? '达到本例评分阈值' : '已到三版上限，分数仍未达标' }}</el-tag>
      <!-- copy始终是本次实际选中或优化后的正文，不是推荐理由。 -->
      <h4>最终文案</h4>
      <!-- 标题只在本节工作流确实产生title时显示，不由前端用截断正文伪造。 -->
      <p v-if="result.title"><strong>{{ result.title }}</strong></p>
      <!-- 助手输出先转义原始HTML再解析Markdown。 -->
      <div class="markdown" v-html="markdown(result.copy)"></div>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { streamRequest } from '@/utils/stream'

// ref创建本次商品输入；脚本读写.value，模板v-model自动解包，不是数据库记录。
const product=ref('声悦降噪耳机，售价299.90元，支持蓝牙连接和主动降噪，续航最长30小时，适合通勤。没有提供优惠、销量或防水等级。')
// 初始允许提交，开始后设true，finally不论成功失败都恢复false。
const busy=ref(false)
// 只保存本次成功的最终State；每次提交前清空，刷新后不会恢复生成内容。
const result=ref(null)
// text 为服务端返回的卖点、候选或正文；返回同步 HTML 字符串供 v-html 显示，不改后端原字符串，也不核验商品事实。
function markdown(text) {
  // 空值先回退空串，依次转义 &、<、>，/g 处理所有出现位置，使原始 HTML 标签以文字显示。
  // 这里只处理原始标签，不是完整 HTML 净化器，不能当作任意不可信 Markdown 的全面安全保证。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // marked.parse 把转义文字解析为 HTML；gfm 启用常见列表/表格等语法，breaks=false 不将普通换行强制变成 br。
  // async=false 保证直接返回字符串给 v-html，而非返回 Promise；它只影响显示转换，不会请求模型。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// channel 保存下拉框的 value：xiaohongshu/douyin/wechat；中文 label 仅显示，提交的键与后端允许值及节点名对应。
const channel=ref('xiaohongshu')
// 每次started事件增加一项；同名节点在循环中有多项，不能只用节点名作为唯一键。
const steps=ref([])
// 后台节点名映射成用户可读文字，既不改变实际执行顺序，也不向用户展示框架对象。
const labels={extract:'提取卖点',xiaohongshu:'小红书文案',douyin:'抖音文案',wechat:'公众号文案',parallel:'并行候选与择优',evaluate:'评估当前版本',optimize:'优化文案',title:'生成最终标题'}
// 无参数，读取商品与渠道发POST事件流；逐事件更新步骤，只有done才展示最终状态。
async function run() {
  // 正在运行时不能重复提交，避免两条事件流混进同一份页面状态。
  if (busy.value) return
  // 后端仍会校验，前端先阻止空白资料产生无效模型请求。
  if (!product.value.trim()) return ElMessage.warning('商品资料不能为空')
  // 新任务清除旧结果和旧步骤，不跨运行复用状态。
  result.value=null
  // 新建数组保留本次事件顺序，循环的每一版都能被看到。
  steps.value=[]
  // 禁用输入直到流结束，避免正在运行时改变显示中的商品条件。
  busy.value=true
  // finished只由done设置，网络结束不代表整张图执行成功。
  let finished=false
  // error事件的提示在连接结束后显示，不追加进正文或当成成功。
  let failure=''
  // streamRequest负责POST、网络分块、中文解码和SSE分帧。
  try {
    // 传JSON正文而不是EventSource的GET查询字符串，字段与ChannelRequest对应。
    await streamRequest('/api/workflow/6/stream',{
      // 只提交商品和渠道，步骤结果由后端实际节点产生。
      data:{product:product.value,channel:channel.value},
      // 事件回调在每帧被完整解析后触发，data已是JSON对象，不再重复JSON.parse。
      onEvent:({event,data})=>{
        // 每个节点先收到started，新增一个执行中步骤；并行候选与择优作为一个阶段展示。
        if (event==='step' && data.status==='started') steps.value.push({node:data.node,status:'process',output:null})
        // 完成事件对应最近一个同名且仍在执行的步骤，不能覆盖上一轮已完成评估。
        if (event==='step' && data.status==='completed') {
          // 从数组尾部找 node 相同且 status=process 的最近记录，回调中的 item 是被检查的每一项。
          // 例如 evaluate 第1版已 finish、第2版仍 process，本次 completed 只匹配第2版，不覆盖旧快照。
          const item=steps.value.findLast(item=>item.node===data.node && item.status==='process')
          // 找到 item 才把该记录从 process 改为 finish，并写入实际 output；引用的是响应式数组原项，页面会随之更新。
          // 若未找到则不臆造开始记录；输出属于这个步骤，不代表后面尚未执行的节点完成。
          if (item) { item.status='finish'; item.output=data.output }
        }
        // done 的 data.result 是最后合并状态，赋给 result 触发最终展示，同时设 finished=true；单个 completed 不会设置它。
        if (event==='done') { result.value=data.result; finished=true }
        // 业务错误保存提示；连接关闭后仍需要检查finished。
        if (event==='error') failure=data.message
      }
    })
    // 没有done就不是成功，把尚在执行的步骤标为失败，已完成步骤与产出仍保留。
    if (!finished) {
      // forEach 检查已有记录，仅将 process 改为 error；已 finish 的结果保留，尚未开始的节点没有记录，也不补成完成。
      steps.value.forEach(item=>{ if (item.status==='process') item.status='error' })
      // 优先显示服务端业务原因，流意外结束时使用清楚的默认提示。
      ElMessage.error(failure || '工作流未完整结束，请重新执行')
    }
  // 公共工具已提示网络或普通JSON错误，这里只把当前执行中步骤标为失败。
  } catch {
    // 不清空已完成步骤，也不虚构done结果，便于对照后端日志定位。
    steps.value.forEach(item=>{ if (item.status==='process') item.status='error' })
  // 无论成功失败都恢复表单，允许用户修改资料后重新执行。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* 白底、内边距和14px正文保持阅读一致；min-width:0允许长文案在父布局内收缩。 */
.workflow-page { background:white; padding:20px; border-radius:10px; font-size:14px; min-width:0; }
/* 渠道框留出上下间距，固定宽度不挤占整个输入区；小屏最多占可用宽度。 */
.channel-select { display:block; width:240px; max-width:100%; margin:12px 0; }
/* 按钮与输入框分开，不把操作紧贴正文。 */
.el-button { margin-top:12px; }
/* 结果区与操作区保持间隔，不把未完成阶段当作最终输出。 */
.result { margin-top:20px; }
/* 三个候选横排，minmax(0,1fr)允许长文本折行，不撑破卡片。 */
.candidates { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:12px 0; }
/* 每版独立卡片，间隔方便核对该版正文和对应分数。 */
.version { margin:12px 0; }
/* 步骤条固定阅读宽度，min-height给单步留出空间，重复评估也按事件顺序追加。 */
.steps { margin:20px 0; min-height:240px; }
/* 各阶段产出默认折叠，避免大段结果挤满进度区域。 */
.step-output { margin:8px 0; }
/* JSON使用等宽13px，保留缩进和换行，长词允许折行，方便核对更新字段。 */
pre { white-space:pre-wrap; overflow-wrap:anywhere; font:13px/1.7 Consolas,monospace; background:#f3f4f6; padding:12px; }
/* 正文按Markdown标签排版，不用pre-wrap制造额外空行；长单词也不溢出。 */
.markdown { font-size:14px; line-height:1.7; overflow-wrap:anywhere; }
/* v-html生成的标签没有本组件scoped属性，通过deep命中段落并控制间距。 */
.markdown :deep(p) { margin:6px 0; }
/* 限制模型标题字号，避免回答中的大标题挤占屏幕。 */
.markdown :deep(h1) { font-size:20px; }
/* 二级标题略小于一级，保持内容层次。 */
.markdown :deep(h2) { font-size:18px; }
/* 更低级标题统一16px，正文仍为14px。 */
.markdown :deep(h3),.markdown :deep(h4),.markdown :deep(h5),.markdown :deep(h6) { font-size:16px; }
/* 列表保留必要缩进，避免项目符号落到卡片外。 */
.markdown :deep(ul),.markdown :deep(ol) { padding-left:24px; }
/* 代码块保留原有缩进和横向滚动，行内代码采用小字号等宽字体。 */
.markdown :deep(code) { font:13px/1.7 Consolas,monospace; }
/* 过长代码不撑宽容器，与普通正文换行策略分开。 */
.markdown :deep(pre) { overflow:auto; white-space:pre; }
/* 小屏将三候选改为一列，避免每列过窄影响录屏和阅读。 */
@media (max-width:900px) { .candidates { grid-template-columns:1fr; } }
</style>

