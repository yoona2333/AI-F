<template>
  <!-- 工具目录来自后端MCP发现结果，表单只提交本次选择和JSON参数。 -->
  <div class="mcp-page">
    <!-- 页面标题说明手动调用用途，不表示模型已自动选择工具。 -->
    <h3>MCP 工具调试</h3>
    <!-- v-model保存所选工具名，change同步清除旧观察；等待时禁止切换条件。 -->
    <el-select v-model="name" :disabled="busy || loading" @change="result=''">
      <!-- 目录中每项按唯一名称区分，label与value均取真实注册名称。 -->
      <el-option v-for="item in tools" :key="item.name" :label="item.name" :value="item.name" />
    </el-select>
    <!-- 刷新目录调用load，loading显示发现等待，busy防止与执行交叉更新。 -->
    <el-button :loading="loading" :disabled="busy || loading" @click="load">读取工具目录</el-button>
    <!-- selected从目录按名称查找，未选择时不读取其属性。 -->
    <section v-if="selected">
      <!-- 工具用途由服务器提供，插值按文本展示。 -->
      <p>{{ selected.description }}</p>
      <!-- Schema按JSON缩进显示，便于核对properties、required及长度。 -->
      <pre>{{ JSON.stringify(selected.inputSchema, null, 2) }}</pre>
    </section>
    <!-- 参数保存为可编辑JSON原文，提交前解析成对象，rows设置初始高度。 -->
    <el-input v-model="argumentsText" type="textarea" :rows="5" :disabled="busy || loading" />
    <!-- 只有选择了工具才可执行，busy显示真实请求等待并阻止重复提交。 -->
    <el-button type="primary" :loading="busy" :disabled="busy || loading || !name" @click="call">调用工具</el-button>
    <!-- result是服务器观察字符串，按文本保留JSON，不做模型Markdown转换。 -->
    <pre v-if="result">{{ result }}</pre>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// tools保存真实name/description/inputSchema目录，初始为空，GET成功后整体替换。
const tools = ref([])
// name只保存所选准确工具名，后端据此请求MCP，不执行页面提供的代码。
const name = ref('')
// 参数编辑区保存JSON字符串，默认示例用于订单或物流工具，商品工具需要改为keyword。
const argumentsText = ref('{"orderNo":"DEMO1001"}')
// result保存本次观察文本，每次调用前清空，失败时不残留旧订单。
const result = ref('')
// loading控制目录发现等待，busy控制调用等待，两者共同锁定操作。
const loading = ref(false)
// busy初始false，调用开始为true，finally恢复false。
const busy = ref(false)
// computed按当前名称从目录查找定义，未找到为undefined，模板v-if保护访问。
const selected = computed(() => tools.value.find(item => item.name === name.value))

// 无参数，读取真实目录并更新列表；网络或业务失败由公共request提示，finally恢复loading。
async function load() {
  // 已有任务时立即返回，不创建交叉请求。
  if (busy.value || loading.value) return
  // 标记发现等待，按钮与选择器同步禁用。
  loading.value = true
  // try等待普通JSON接口，异常不覆盖现有目录。
  try {
    // GET对应后端工具发现入口，不调用模型。
    const response = await request.get('/api/mcp/client/tools')
    // 仅字符串业务码200表示目录发现成功。
    if (response.code === '200') {
      // 替换目录，名称不再存在时清空选择，避免沿用已失效定义。
      tools.value = response.data
      // some检查新目录是否仍有当前名称；没有则等待用户重新选择。
      if (!tools.value.some(item => item.name === name.value)) name.value = ''
    }
  // 公共封装已提示，页面只负责等待状态。
  } catch {
  // 成功或失败均恢复读取按钮。
  } finally { loading.value = false }
}

// 无参数，解析JSON对象后提交name/arguments，成功写入result；非法JSON在请求前提示。
async function call() {
  // 等待中或未选择工具时不发送。
  if (busy.value || loading.value || !name.value) return
  // 局部变量接收解析后的对象，避免将JSON原文字符串交给后端。
  let args
  // JSON解析错误由本页提示，网络异常仍由公共request处理。
  try {
    // 从文本生成JavaScript对象，语法错误会抛异常。
    args = JSON.parse(argumentsText.value)
    // null和数组都不是本接口要求的参数对象。
    if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('参数必须是JSON对象')
  // 输入不合格时结束，不改变busy，也不执行工具。
  } catch { return ElMessage.warning('参数必须是有效JSON对象') }
  // 本轮请求开始前清空旧观察。
  result.value = ''
  // 标记真实调用等待，阻止重复提交。
  busy.value = true
  // 请求异常交给公共封装提示。
  try {
    // 字段对应CallRequest.name与arguments，timeout限制本次HTTP等待为60秒。
    const response = await request.post('/api/mcp/client/call',{name: name.value, arguments: args},{timeout: 60000})
    // 成功才展示服务器原结果，found=false仍是一份有效观察。
    if (response.code === '200') result.value = response.data.result
  // 公共封装已提示错误，保留空结果。
  } catch {
  // 所有请求结束路径恢复按钮与输入。
  } finally { busy.value = false }
}

// 挂载完成后读取工具目录，传函数引用使Vue在正确生命周期调用。
onMounted(load)
</script>
<style scoped>
/* 页面内边距、白底和基础字号保持表单及观察易读；min-width允许长字段收缩。 */
.mcp-page { padding:20px; background:white; font-size:14px; min-width:0; }
/* 参数、Schema及结果保留缩进，长行折行，使用等宽字体核对JSON。 */
pre { white-space:pre-wrap; overflow-wrap:anywhere; padding:12px; background:#f3f4f6; font:13px/1.7 Consolas,monospace; }
/* 按钮和文本框上方留间距，避免紧贴前一操作区。 */
.el-button,.el-textarea { margin-top:12px; }
</style>

