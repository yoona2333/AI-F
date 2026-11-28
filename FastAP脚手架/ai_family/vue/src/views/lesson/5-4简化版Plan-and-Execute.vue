<template>
  <!-- 输入与本次查询结果分开显示，刷新后重新开始。 -->
  <div class="agent-page">
    <!-- 标题标明先规划再执行的任务方式。 -->
    <h3>商品对比计划</h3>
    <!-- question是唯一请求字段，busy期间锁定输入，长度对应请求模型上限。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="2000" :disabled="busy" />
    <!-- 提交后等待规划、查询和汇总全部结束，loading与禁用共同读取busy。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="run">制定计划并执行</el-button>
    <!-- 只有本轮成功结果才显示，卡片展示完成后的真实记录。 -->
    <section v-if="result">
      <!-- 原计划和执行记录分别显示，可核对是否按相同顺序查询。 -->
      <h4>查询计划</h4>
      <!-- index来自清单顺序，每项只显示经过后端校验的关键词。 -->
      <ol><li v-for="(item,index) in result.plan.steps" :key="index">查询商品：{{ item.keyword }}</li></ol>
      <!-- 每次查询成功后服务才追加该记录，status=completed来自真实返回。 -->
      <el-card v-for="item in result.steps" :key="item.index" class="tool-step" shadow="never">
        <!-- 步骤号对应计划位置，完成状态不通过定时器模拟。 -->
        <template #header>步骤 {{ item.index }}：{{ item.keyword }} · {{ item.status === 'completed' ? '已完成' : item.status }}</template>
        <!-- result包含products数组，空数组也按原样展示，不填入示例商品。 -->
        <pre>{{ JSON.stringify(item.result,null,2) }}</pre>
      </el-card>
      <!-- answer是模型根据实际查询记录生成的Markdown原文，标题下面仅做显示转换。 -->
      <h4>汇总建议</h4>
      <!-- markdown返回同步HTML，v-html插入div以容纳段落、列表、表格和代码块；result.answer原文保持不变。 -->
      <div class="answer" v-html="markdown(result.answer)"></div>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'

// 演示问题包含三类已有商品，用户也可以修改关键词后提交。
const question=ref('对比耳机、音箱和平板的价格和库存，给我购买建议。')
// busy统一控制本次等待与表单禁用，初始允许操作。
const busy=ref(false)
// result只保存本次成功的plan、steps和answer，请求前清空。
const result=ref(null)
// 输入汇总回答原文，返回同步HTML给v-html；只转换显示格式，不修改计划、查询记录或result.answer。
function markdown(text) {
  // 空值回退空串，依次转义&、<、>，/g替换全部出现位置；先处理&以免后续生成的实体被重复转义。
  const escaped=(text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  // gfm支持表格等常见语法，breaks=false采用Markdown普通换行规则，async=false直接返回HTML而非Promise。
  return marked.parse(escaped,{gfm:true,breaks:false,async:false})
}
// 读取当前问题，等待完整JSON结果，更新页面；异常由公共封装提示，finally恢复操作。
async function run() {
  // 防止正在执行时再次提交，避免两次结果交叉覆盖。
  if (busy.value) return
  // 前端阻止空白，后端仍有独立的长度和空白校验。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 移除上一轮结果，本轮失败也不会展示旧商品建议。
  result.value=null
  // 等待期间锁定本次问题并显示加载图标。
  busy.value=true
  // 公共request处理业务及网络错误，本页管理展示状态。
  try {
    // question是用户原文，300000毫秒限制HTTP等待，不改变两次模型调用的执行顺序。
    const response=await request.post('/api/agent/plan/run',{question:question.value},{timeout:300000})
    // 只有业务成功才显示计划、实际查询和最终汇总。
    if (response.code==='200') result.value=response.data
  // 公共封装已弹出错误，当前result保持null。
  } catch {
  // 成功或失败都恢复输入和按钮。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* 14px基础字号及白底保持输入和结果的阅读一致性。 */
.agent-page { padding:20px; background:white; border-radius:10px; font-size:14px; min-width:0; }
/* 按钮、结果区、各步骤之间留出间距。 */
.el-button,section,.tool-step { margin-top:12px; }
/* Markdown按生成标签排版，长词折行，宽表格在答案区横向滚动，不用pre-wrap额外保留段落间空行。 */
.answer { overflow-wrap:anywhere; line-height:1.7; overflow-x:auto; }
/* v-html内部标签没有组件scoped标记，使用deep命中生成段落并设置上下间距。 */
.answer :deep(p) { margin:6px 0; }
/* 一级标题限制为20px，保持结果区的阅读比例。 */
.answer :deep(h1) { font-size:20px; }
/* 二级标题使用18px，与一级形成层次。 */
.answer :deep(h2) { font-size:18px; }
/* 三至六级标题统一16px，正文继承页面的14px。 */
.answer :deep(h3),.answer :deep(h4),.answer :deep(h5),.answer :deep(h6) { font-size:16px; }
/* 列表保留24px左缩进，使项目符号与序号位于容器内。 */
.answer :deep(ul),.answer :deep(ol) { padding-left:24px; }
/* 合并相邻表格边框，上下留出间距，便于阅读价格和库存对比。 */
.answer :deep(table) { border-collapse:collapse; margin:10px 0; }
/* 表头与数据单元格设置相同边框及内边距，使商品字段清楚分列。 */
.answer :deep(th),.answer :deep(td) { border:1px solid #dcdfe6; padding:6px 10px; }
/* Markdown代码块保留缩进和长行，在块内滚动；工具记录的pre仍使用下方折行样式。 */
.answer :deep(pre) { white-space:pre; overflow:auto; padding:12px; background:#f3f4f6; }
/* 行内代码与代码块内容统一使用13px等宽字体及1.7行高。 */
.answer :deep(code) { font:13px/1.7 Consolas,monospace; }
/* 查询记录的JSON保留缩进和换行，长字段折行以适应窄屏。 */
pre { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.7; }
/* JSON以等宽字体显示，方便核对名称、价格和库存。 */
pre { padding:12px; background:#f3f4f6; font:13px/1.7 Consolas,monospace; }
</style>

