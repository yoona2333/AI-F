<template>
  <!-- 页面只提交本次商品资料，生成阶段和结果由服务端真实工作流决定。 -->
  <div class="workflow-page">
    <!-- 标题对应当前课节示例，表单输入和结果都采用统一阅读字号。 -->
    <h3>文案评估与优化</h3>
    <!-- v-model 双向绑定 product，textarea 使用多行输入，rows=4 为初始高度，maxlength=3000 对应资料长度上限。 -->
    <!-- busy 为 true 时 disabled 锁住本次条件，防止执行中修改表单；接口仍必须独立校验，前端限制不能代替后端。 -->
    <el-input v-model="product" type="textarea" :rows="4" :maxlength="3000" :disabled="busy" />
    <!-- 点击才调用 run；loading 显示等待，disabled 禁止重复点击，二者读取 busy；开始前设 true，结束后 finally 复原。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="run">开始生成</el-button>
    <!-- 成功拿到本轮完整状态后才展示最终结果，异常不保留上一轮的成功内容。 -->
    <section v-if="result" class="result">
      <!-- 卖点与原始资料分开，便于判断模型有没有添加用户未给出的事实。 -->
      <h4>提取卖点</h4>
      <!-- Markdown只影响显示，state中的原始字符串不被修改。 -->
      <div class="markdown" v-html="markdown(result.points)"></div>
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
      <!-- copy 是最后一次评估的当前正文；达到三版上限仍可能低分，结合下方分数和版本记录核对。 -->
      <h4>最终文案</h4>
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

// ref创建本次商品输入；脚本读写.value，模板v-model自动解包，不是数据库记录。
const product=ref('声悦降噪耳机，售价299.90元，支持蓝牙连接和主动降噪，续航最长30小时，适合通勤。没有提供优惠、销量或防水等级。')
// 初始允许提交，开始后设true，finally不论成功失败都恢复false。
const busy=ref(false)
// 只保存本次成功的最终State；每次提交前清空，刷新后不会恢复生成内容。
const result=ref(null)
// text 为服务端返回的卖点或各版正文；返回同步 HTML 字符串供 v-html 显示，不改后端原字符串，也不核验商品事实。
function markdown(text) {
  // 空值先回退空串，依次转义 &、<、>，/g 处理所有出现位置，使原始 HTML 标签以文字显示。
  // 这里只处理原始标签，不是完整 HTML 净化器，不能当作任意不可信 Markdown 的全面安全保证。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // marked.parse 把转义文字解析为 HTML；gfm 启用常见列表/表格等语法，breaks=false 不将普通换行强制变成 br。
  // async=false 保证直接返回字符串给 v-html，而非返回 Promise；它只影响显示转换，不会请求模型。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// 无输入参数，提交当前表单并等待整图完成；页面状态通过赋值更新，函数不返回业务对象。
async function run() {
  // 请求中或空白资料均不再次调用模型，后端仍有自己的校验。
  if (busy.value) return
  // trim仅用于判断，不改变提交给节点的原始资料。
  if (!product.value.trim()) return ElMessage.warning('商品资料不能为空')
  // 新运行先清空 result，v-if 结果区随之移除；这次失败也不会保留上一次商品的成功内容。
  result.value=null
  // 加载状态与disabled同时生效，防止连续点击触发多次工作流。
  busy.value=true
  // 公共request已经处理统一业务及网络错误，这里只负责结束等待。
  try {
    // 多个节点可能有多次模型调用，600000毫秒是本次HTTP等待上限，不改变公共封装。
    const response=await request.post('/api/workflow/5/run',{product:product.value},{timeout:600000})
    // code 必须为业务约定的字符串 "200"，才把最终 State 赋给 result；ref 更新触发模板重绘，失败不填固定结果。
    if (response.code==='200') result.value=response.data
  // 公共封装已显示错误，不再重复弹窗。
  } catch {
  // finally在成功、异常或提前返回时都执行，避免页面一直禁用。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* 白底、内边距和14px正文保持阅读一致；min-width:0允许长文案在父布局内收缩。 */
.workflow-page { background:white; padding:20px; border-radius:10px; font-size:14px; min-width:0; }
/* 按钮与输入框分开，不把操作紧贴正文。 */
.el-button { margin-top:12px; }
/* 结果区与操作区保持间隔，不把未完成阶段当作最终输出。 */
.result { margin-top:20px; }
/* 每版独立卡片，间隔方便核对该版正文和对应分数。 */
.version { margin:12px 0; }
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
</style>

