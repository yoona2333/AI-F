<template>
  <!-- 输入卡片和结果卡片按上下顺序展示。 -->
  <div class="structured-page">
    <!-- 输入商品描述，不要求用户先手写 JSON。 -->
    <el-card>
      <!-- 标题说明本页操作。 -->
      <h3>把商品描述变成字段</h3>
      <!-- 双向绑定描述，五行输入；最多 2000 字，显示字数，等待时禁用。 -->
      <el-input v-model="description" type="textarea" :rows="5" maxlength="2000" show-word-limit :disabled="busy" />
      <!-- 点击提取；请求期间显示加载状态并禁用按钮。 -->
      <el-button class="extract-button" type="primary" :loading="busy" :disabled="busy" @click="extract">提取商品信息</el-button>
    </el-card>
    <!-- null 表示未提及，零元价格仍正常展示。 -->
    <el-card v-if="product" class="product-card">
      <!-- null 使用未提及占位，普通文本通过插值展示。 -->
      <h3>品牌：{{ product.brand ?? '未提及' }}</h3>
      <!-- 明确比较 null，避免把合法的零元价格当作缺失。 -->
      <p class="price">价格：{{ product.price === null ? '未提及' : `¥ ${product.price}` }}</p>
      <!-- 卖点标签允许自动换行。 -->
      <div class="selling-points">
        <!-- 遍历卖点，以当前列表的位置作为 key，标签展示每条正文。 -->
        <el-tag v-for="(point, index) in product.sellingPoints" :key="index">{{ point }}</el-tag>
      </div>
      <!-- 空列表时显示提示。 -->
      <p v-if="!product.sellingPoints.length">没有明确的卖点。</p>
      <!-- 将对象格式化为两空格缩进的 JSON，便于核对字段。 -->
      <pre class="product-json">{{ JSON.stringify(product, null, 2) }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 示例描述，页面发送原文，由后端提取字段。
const description = ref('品牌是声悦，售价 299.90 元，支持主动降噪和蓝牙连接，续航 30 小时。')
// 初始没有结果，成功后保存接口返回的商品对象。
const product = ref(null)
// 等待回复期间禁用输入和按钮，避免重复发送。
const busy = ref(false)

// 无输入参数，发送当前描述并更新商品卡片；失败由公共请求封装提示。
async function extract() {
  // 已有请求进行中时不重复提取。
  if (busy.value) return
  // 页面先检查空白，后端仍会执行字段校验。
  if (!description.value.trim()) return ElMessage.warning('商品描述不能为空')
  // 进入等待状态。
  busy.value = true
  // 清除旧卡片，避免将上一次结果误认为本次结果。
  product.value = null
  // 请求结束后都要恢复页面操作。
  try {
    // 提交原始描述，返回结果采用脚手架统一的 code、data 结构。
    const result = await request.post('/api/structured/product', { description: description.value })
    // 仅业务成功时显示商品对象，无需再次 JSON.parse。
    if (result.code === '200') product.value = result.data
  // 公共请求封装已经提示错误，不重复弹窗。
  } catch {
  // 无论成功还是失败，都恢复按钮和输入框。
  } finally {
    // 结束等待状态。
    busy.value = false
  }
}
</script>
<style scoped>
/* 网格布局让两张卡片上下排列，卡片之间留出间距。 */
.structured-page { display: grid; gap: 18px; font-size: 14px; }
/* 标题保持紧凑，避免卡片文字过大。 */
.structured-page h3 { font-size: 16px; }
/* 按钮与输入框留出间隔。 */
.extract-button { margin-top: 14px; }
/* 用蓝色突出价格，字号略大于正文。 */
.price { color: #1565c0; font-size: 16px; }
/* 标签横向排列，空间不足时换行，每条之间留出间距。 */
.selling-points { display: flex; flex-wrap: wrap; gap: 10px; }
/* JSON 保留缩进与换行，长文本可折行，使用小字号和浅灰背景。 */
.product-json { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f4f6; padding: 14px; font-size: 13px; line-height: 1.6; }
</style>

