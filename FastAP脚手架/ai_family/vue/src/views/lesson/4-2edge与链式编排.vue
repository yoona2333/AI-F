<template>
  <!-- 页面只提交本次商品资料，生成阶段和结果由服务端真实工作流决定。 -->
  <div class="workflow-page">
    <!-- 标题对应当前课节示例，表单输入和结果都采用统一阅读字号。 -->
    <h3>链式文案生成</h3>
    <!-- v-model 把输入文字同步到 product；type=textarea 使用多行文本，rows=4 指定初始高度，maxlength 限制最多3000字符。 -->
    <!-- :disabled 读取 busy，运行期间锁住本次输入；前端限制只帮助操作，接口仍独立做长度和非空白校验。 -->
    <el-input v-model="product" type="textarea" :rows="4" :maxlength="3000" :disabled="busy" />
    <!-- @click 在用户点击时调用脚本 run；:loading 显示忙碌图标，:disabled 禁止继续点击，两者共同读取 busy。 -->
    <!-- busy 在发请求前设 true，finally 恢复 false；本页加载不会自动调用收费模型。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="run">开始生成</el-button>
    <!-- 成功拿到本轮完整状态后才展示最终结果，异常不保留上一轮的成功内容。 -->
    <section v-if="result" class="result">
      <!-- 卖点与原始资料分开，便于判断模型有没有添加用户未给出的事实。 -->
      <h4>提取卖点</h4>
      <!-- result.points 来自后端 extract 节点的合并结果；markdown 转为 HTML，v-html 将其放入当前区域，不回写原字符串。 -->
      <div class="markdown" v-html="markdown(result.points)"></div>
      <!-- result.copy 是 draft 节点生成的正文，本节没有候选评选或循环优化；标签只负责给结果分区。 -->
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
import request from '@/utils/request'

// product 保存当前输入框文字，初始字符串只是可编辑的商品事实示例，不是预设生成结果。
// ref 让它具备响应式更新；脚本用 product.value 取值，模板 v-model 自动解包，不需要写 .value。
const product=ref('声悦降噪耳机，售价299.90元，支持蓝牙连接和主动降噪，续航最长30小时，适合通勤。没有提供优惠、销量或防水等级。')
// 初始允许提交，开始后设true，finally不论成功失败都恢复false。
const busy=ref(false)
// 只保存本次成功的最终State；每次提交前清空，刷新后不会恢复生成内容。
const result=ref(null)
// text 是卖点或正文字符串；返回同步解析后的 HTML 给模板 v-html，原 result 中的文字保持不变。
// 该函数只负责显示格式，不检查文案事实；模型调用在后端完成，前端不会生成新的卖点。
function markdown(text) {
  // text 为空时回退空串；先转义 &，再转义 < 和 >，使原始标签按文字显示；/g 表示处理所有匹配处。
  // 这里仅做原始标签转义，不是完整 HTML 净化器，不能把它当作任意不可信 Markdown 的全面安全保证。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // marked.parse 把转义后的文字转成 HTML；gfm 启用列表和表格等语法，breaks=false 不把普通换行强制转成 br。
  // async=false 让这里直接返回字符串而非 Promise，模板才能同步拿到 v-html 需要的内容。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// 无参数，读取 product.value，提交 POST 后等待完整状态；函数通过 result、busy 更新当前页面，不返回业务数据。
// 空白输入直接提示；请求失败由公共封装提示，保留空结果并在 finally 恢复按钮，不把旧结果冒充本轮生成。
async function run() {
  // 请求中或空白资料均不再次调用模型，后端仍有自己的校验。
  if (busy.value) return
  // trim仅用于判断，不改变提交给节点的原始资料。
  if (!product.value.trim()) return ElMessage.warning('商品资料不能为空')
  // 新请求先把 result 置空，v-if 结果区随之移除；即使这次失败，也不会残留上一商品的成功文案。
  result.value=null
  // 加载状态与disabled同时生效，防止连续点击触发多次工作流。
  busy.value=true
  // 公共request已经处理统一业务及网络错误，这里只负责结束等待。
  try {
    // 第一个参数是本节路由地址，第二个参数的 product 对应 CopyRequest.product；提交的是原事实，不是生成结果。
    // 第三个参数只把本次 HTTP 等待设为600000毫秒（10分钟），容纳三个顺序节点；它不会修改单个模型请求的超时。
    const response=await request.post('/api/workflow/2/run',{product:product.value},{timeout:600000})
    // 公共响应约定 code 为字符串 "200"，只有业务成功才把完整 data 赋给 result.value。
    // ref 更新后模板重绘：points 到卖点区，title 到标题行，copy 到正文区；其他响应不填入结果区。
    if (response.code==='200') result.value=response.data
  // 公共封装已显示错误，不再重复弹窗。
  } catch {
  // 请求成功或 try 内抛异常都会进入 finally，恢复 busy；上方空白判断发生在 try 之前，那里尚未设忙碌。
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

