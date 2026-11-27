<template>
  <!-- 本页只处理当前完整问题，表单输入和工具执行记录分别展示。 -->
  <div class="agent-page">
    <!-- 标题描述实际手写循环，不把页面加载状态说成模型内心思考。 -->
    <h3>手写 ReAct 查询助手</h3>
    <!-- question双向绑定当前问题；rows指定初始行数，maxlength对应后端2000字符限制，busy期间禁止改动。 -->
    <el-input v-model="question" type="textarea" :rows="3" :maxlength="2000" :disabled="busy" />
    <!-- 点击才调用run，loading显示等待，disabled阻止重复提交；结束时finally统一恢复busy。 -->
    <el-button type="primary" :loading="busy" :disabled="busy" @click="run">查询并回答</el-button>
    <!-- result只在本轮成功响应后赋值；请求开始清空，避免失败时残留旧问题的结果。 -->
    <section v-if="result">
      <!-- completed来自后端，达到5轮上限也可收到普通JSON，但必须显示未完成，不能只看HTTP成功。 -->
      <el-tag :type="result.completed ? 'success' : 'warning'">{{ result.completed ? '已生成最终回答' : '达到上限，尚未完成' }}</el-tag>
      <!-- answer是最终文字或明确的上限提示；插值按纯文本显示，white-space保留换行。 -->
      <p class="answer">{{ result.answer }}</p>
      <!-- 展示实际执行过的记录，模型直接回答时steps为空，不捏造工具过程。 -->
      <h4>本次工具记录</h4>
      <!-- 只有本轮记录为空才出现空状态，不要求模型为凑演示调用不必要工具。 -->
      <el-empty v-if="!result.steps.length" description="本次没有执行工具" />
      <!-- round为本次模型决策编号，一轮最多一个工具，用它标识已执行记录。 -->
      <el-card v-for="item in result.steps" :key="item.round" class="tool-step" shadow="never">
        <!-- 名称与模型请求和允许工具集合一致，不从回答文字反推出工具。 -->
        <template #header>第 {{ item.round }} 轮：{{ item.toolName }}</template>
        <!-- arguments是本次实际执行的参数对象，JSON.stringify以两空格缩进便于核对订单号。 -->
        <pre>参数：{{ JSON.stringify(item.arguments, null, 2) }}</pre>
        <!-- result是工具真实返回的JSON文本，按纯文本显示，不作为HTML执行。 -->
        <pre>观察结果：{{ item.result }}</pre>
      </el-card>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 本次输入的完整问题，初始订单号来自演示数据；用户可修改，新请求不会带入旧问题或工具记录。
const question=ref('请查询订单 DEMO1001 的订单状态和物流最新情况。')
// busy初始为false，发送前设true；同时控制输入框、按钮禁用和等待图标。
const busy=ref(false)
// result保存服务返回的answer/completed/steps，初始null不展示结果，刷新页面会重新初始化。
const result=ref(null)
// 无参数，读取question并提交JSON；响应更新result，失败由公共请求封装提示，始终恢复busy，不返回业务对象。
async function run() {
  // 已在等待时直接结束，防止多个请求的结果混入同一页。
  if (busy.value) return
  // trim仅用于判断全空白，不修改实际提交的原问题；后端还有独立校验。
  if (!question.value.trim()) return ElMessage.warning('问题不能为空')
  // 清空旧结果区，不能把上次查到的物流当作本轮成功内容。
  result.value=null
  // 开始等待，模板响应式更新禁用输入和按钮。
  busy.value=true
  // 公共request已负责网络与业务错误提示，这里管理本次页面状态。
  try {
    // JSON的question对应ReactRequest.question；300000毫秒是整个HTTP等待上限，容纳最多5次顺序模型请求。
    const response=await request.post('/api/agent/react/run',{question:question.value},{timeout:300000})
    // 只有字符串业务码200时更新页面；completed再区分最终回答或上限退出，不补固定查询数据。
    if (response.code==='200') result.value=response.data
  // 错误已由公共封装提示，result仍为null，不重复弹窗。
  } catch {
  // 请求成功或try内异常都会恢复操作；前面的输入检查发生在设busy之前。
  } finally { busy.value=false }
}
</script>
<style scoped>
/* 本页白底、14px基础字号，内边距留出阅读空间，min-width允许长字段在父布局中收缩。 */
.agent-page { padding:20px; background:white; border-radius:10px; font-size:14px; min-width:0; }
/* 操作按钮与文本框保持间距，结果标签也与上方操作区分开。 */
.el-button,section { margin-top:12px; }
/* 回答按纯文本保留换行，长编号或连续文字允许折行，不解析模型HTML。 */
.answer { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.7; }
/* 每项工具记录独立卡片，间距使轮次、参数和观察容易对应。 */
.tool-step { margin-top:12px; }
/* JSON保留缩进和换行，13px等宽字体便于逐项核对，长行在容器内部折行。 */
pre { white-space:pre-wrap; overflow-wrap:anywhere; padding:12px; background:#f3f4f6; font:13px/1.7 Consolas,monospace; }
</style>

