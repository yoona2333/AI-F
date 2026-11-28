<template>
  <!-- 本页输入一个完整问题；question保存输入，result保存本次接口返回的最终回答及真实工具记录。 -->
  <div class="agent-page">
    <!-- h3显示当前页面名称；执行进度由按钮的loading状态提示，结果区在接口返回后显示。 -->
    <h3>框架 ReAct 查询助手</h3>
    <!-- v-model将多行输入与question双向绑定，模板自动解包ref；脚本读写则使用question.value。 -->
    <!-- type=textarea使用多行框，rows=3设置初始高度，maxlength=2000对应后端字符上限，disabled=busy锁定本次输入。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="2000" :disabled="busy" />
    <!-- @click绑定run函数，点击时才提交；primary使用主题色，loading=busy显示等待，disabled=busy阻止再次点击。 -->
    <!-- run开始前设置busy=true，请求结束在finally恢复false，输入框和按钮同时恢复操作。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="run">查询并回答</el-button>
    <!-- v-if只在result非空时创建结果区；run先清空旧result，只有本次业务码为字符串200才赋入服务端data。 -->
    <section v-if="result">
      <!-- completed来自服务端完整性检查；:type按布尔值选择绿色success或黄色warning，插值同步显示状态文字。 -->
      <el-tag :type="result.completed ? 'success' : 'warning'">{{ result.completed ? '已生成最终回答' : '尚未完成' }}</el-tag>
      <!-- markdown读取result.answer原字符串，返回HTML；v-html将其插入div内部，div可容纳段落、列表、表格等块元素。 -->
      <!-- 显示转换不修改result.answer，也不重新生成回答；原始工具观察仍由下方pre按纯文本展示。 -->
      <div class="answer" v-html="markdown(result.answer)"></div>
      <!-- steps由后端将模型工具请求与ToolMessage观察按调用编号配对后生成，标题下面逐项展示真实记录。 -->
      <h4>本次工具记录</h4>
      <!-- steps.length为0时取反得到true，el-empty显示空记录提示；模型直接询问补充信息时可以没有工具记录。 -->
      <el-empty v-if="!result.steps.length" description="本次没有执行工具" />
      <!-- v-for遍历后端steps，每个item是一份已完成工具记录；:key使用准确toolCallId，同名工具多次执行也能区分。 -->
      <!-- shadow=never关闭卡片阴影；tool-step类为每项增加间距，卡片顺序采用服务返回的观察消息顺序。 -->
      <el-card v-for="item in result.steps" :key="item.toolCallId" class="tool-step" shadow="never">
        <!-- #header是el-card的标题插槽；round来自后端AI消息计数，toolName来自真实工具请求name，不是数组下标。 -->
        <template #header>第 {{ item.round }} 轮：{{ item.toolName }}</template>
        <!-- arguments是参数对象；JSON.stringify的第二项null保留所有字段，第三项2按两空格缩进。 -->
        <!-- 双花括号按文本显示序列化结果，pre保留JSON缩进，便于核对orderNo或query等实际查询条件。 -->
        <pre>参数：{{ JSON.stringify(item.arguments, null, 2) }}</pre>
        <!-- item.result是这项工具返回的观察文本，不是页面顶层result对象；插值直接展示，不再次解析或执行其中HTML。 -->
        <pre>观察结果：{{ item.result }}</pre>
      </el-card>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'

// ref创建响应式问题字符串，初始订单号来自演示数据；模板输入更新question，POST读取question.value原文。
const question=ref('请查询订单 DEMO1001 的状态和物流，并检索退换货政策，说明我该如何申请退货。')
// busy是本次HTTP请求的等待标记，初始false允许输入；设true时同时触发文本框禁用、按钮禁用和加载图标。
const busy=ref(false)
// result初始null使v-if隐藏结果；成功后保存response.data对象，模板读取answer、completed、steps，刷新后重新初始化。
const result=ref(null)
// Markdown显示函数：text是服务端answer原文，返回同步HTML字符串给v-html，不修改后端结果对象。
// 先转义原始HTML字符，再由marked解析Markdown；此函数只做格式转换，不请求模型或校验商品事实。
function markdown(text) {
  // text为空值时用空串；三个replace依次转义&、<、>，正则/g替换所有出现位置。
  // 先处理&，避免后面新产生的&lt;和&gt;再次被转义；原始HTML标签因此以文字显示。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // marked.parse读取escaped并生成HTML；gfm=true支持表格等常见语法，breaks=false保留Markdown普通换行规则。
  // async=false让返回值直接是HTML字符串，模板无需等待Promise；result.answer中的Markdown原文仍保留。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// 页面提交函数：无输入参数，读取question.value发POST，整次Agent正常返回后将data写入result供模板展示。
// 函数不返回业务数据；空白时提示并结束，业务或网络失败由公共request提示，finally统一恢复busy。
async function run() {
  // busy.value为true说明上一请求尚未结束，return立即结束函数，不再发出第二次模型工作流请求。
  if (busy.value) return
  // trim只用于判断全空白，warning显示提示后return；此检查在busy设true之前，实际POST仍发送未经trim的原文。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 将ref内容置null会触发模板更新，v-if移除上一轮结果；本次失败也不会显示旧订单或政策答案。
  result.value=null
  // 发请求前把等待标记设true，模板自动解包busy并更新disabled与loading，此时本次问题不能再编辑。
  busy.value=true
  // try覆盖HTTP等待和成功赋值；公共request封装负责通用错误提示，本页负责结果与加载状态。
  try {
    // POST第一个参数是接口地址，第二个是JSON正文，仅含question；它对应后端ReactRequest.question。
    // 第三个参数是本次HTTP配置，timeout=300000即最多等待300秒；await等待整次Agent返回，不是单个工具结束。
    const response=await request.post('/api/agent/framework/run',{question:question.value},{timeout:300000})
    // response是公共request返回的业务对象；仅code严格等于字符串200时将data写入result，触发结果区渲染。
    // data中的completed来自后端最终消息检查；本节图步数耗尽会返回错误，不会在这里构造一个上限退出结果。
    if (response.code==='200') result.value=response.data
  // 请求抛错进入catch，公共封装已经提示；保持请求前清空的result，不再追加第二条相同弹窗。
  } catch {
  // finally在try正常结束或抛异常后都会执行，将busy恢复false；上方提前返回的输入检查发生在设busy之前。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* 页面设白底、20px内边距、10px圆角与14px基础字号；min-width:0允许长工具字段随父布局收缩。 */
.agent-page { padding:20px; background:white; border-radius:10px; font-size:14px; min-width:0; }
/* 逗号分别选择按钮和section，两者上方各留12px，分开输入、操作与结果区域。 */
.el-button,section { margin-top:12px; }
/* Markdown由生成的段落标签控制换行，line-height=1.7保持可读性；长词折行，宽表格在答案区横向滚动。 */
.answer { overflow-wrap:anywhere; line-height:1.7; overflow-x:auto; margin-top:12px; }
/* v-html内部标签没有当前组件的scoped标记，:deep(p)才能命中生成段落并设置上下6px间距。 */
.answer :deep(p) { margin:6px 0; }
/* 一级标题限为20px，避免模型大标题占满结果区。 */
.answer :deep(h1) { font-size:20px; }
/* 二级标题使用18px，保留比一级更低的视觉层级。 */
.answer :deep(h2) { font-size:18px; }
/* 三至六级标题统一16px，正文仍继承页面14px。 */
.answer :deep(h3),.answer :deep(h4),.answer :deep(h5),.answer :deep(h6) { font-size:16px; }
/* 有序与无序列表都保留24px左缩进，使序号或圆点位于容器内。 */
.answer :deep(ul),.answer :deep(ol) { padding-left:24px; }
/* 合并表格相邻边框，上下留10px；超过答案区宽度时由外层overflow-x:auto提供滚动。 */
.answer :deep(table) { border-collapse:collapse; margin:10px 0; }
/* 表头th与普通单元格td使用相同边框和内边距，价格与库存等列能清楚分隔。 */
.answer :deep(th),.answer :deep(td) { border:1px solid #dcdfe6; padding:6px 10px; }
/* Markdown代码块保留原始缩进和长行，overflow:auto在代码块内部滚动。 */
.answer :deep(pre) { white-space:pre; overflow:auto; padding:12px; background:#f3f4f6; }
/* code同时覆盖行内代码和代码块内容，13px等宽字体与1.7行高便于阅读参数。 */
.answer :deep(code) { font:13px/1.7 Consolas,monospace; }
/* 工具卡片上方留12px，分开多条真实调用的标题、参数与观察。 */
.tool-step { margin-top:12px; }
/* 模板中的工具记录pre保留JSON缩进与换行，长字段可折行；灰底、12px内边距和13px等宽字体便于核对。 */
pre { white-space:pre-wrap; overflow-wrap:anywhere; padding:12px; background:#f3f4f6; font:13px/1.7 Consolas,monospace; }
</style>

