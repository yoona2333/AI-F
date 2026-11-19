<template>
  <div class="prompt-chat-page">
    
    <section class="content-panel">
   
    <h3>选择角色并提问</h3>
    
    <el-form label-position="top" :disabled="loading">
      <el-form-item label="角色">
        <el-select v-model="form.role" class="role-select" :disabled="loading" @change="changeRole">
          <el-option label="编程" value="java" /><el-option label="翻译" value="translator" /><el-option label="文案" value="copywriter" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.role === 'java'" label="学习水平">
        <el-select v-model="form.audience" :disabled="loading"><el-option label="入门" value="入门" /><el-option label="进阶" value="进阶" /></el-select>
      </el-form-item>
      <el-form-item v-if="form.role === 'translator'" label="目标语言">
        <el-select v-model="form.targetLanguage" :disabled="loading"><el-option v-for="language in languages" :key="language" :label="language" :value="language" /></el-select>
      </el-form-item>
      <el-form-item v-if="form.role === 'copywriter'" label="商品名"><el-input v-model="form.productName" maxlength="80" :disabled="loading" /></el-form-item>
      <el-form-item label="输入内容"><el-input v-model="form.question" type="textarea" :rows="4" maxlength="2000" :disabled="loading" /></el-form-item>
      <el-form-item><el-button class="send-button" type="primary" :loading="loading" @click="send">发送</el-button></el-form-item>
    </el-form>
    </section>
    <!-- 右侧只展示当前回答和实际系统消息。 -->
    <section class="content-panel">
      <h3>本次回答</h3>
      <p v-if="loading">大模型正在生成回答，请稍候……</p>
      <el-empty v-if="!result && !loading" description="选择角色后发送问题" />
      <!-- 成功返回后显示本次角色、模型和回答。 -->
      <div v-if="result">
        <p>{{ roleLabels[result.role] }} · {{ result.modelName }}</p>
       
        <div class="answer-content" v-html="renderMarkdown(result.answer)"></div>
        <h3>本次 System 消息</h3>

        <pre class="system-text">{{ result.systemPrompt }}</pre>
      </div>
    </section>
  </div>
</template>
<script setup>
// 1-3 页面：提交角色和变量，展示返回的回答与实际系统消息。
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import request from '@/utils/request'




const roleLabels = { java: '编程', translator: '翻译', copywriter: '文案' }
const languages = ['英语', '中文', '日语']
const examples = { java: '用一个例子解释 Java 的接口。', translator: '这副耳机支持主动降噪，适合通勤。', copywriter: '支持主动降噪，佩戴舒适，适合通勤。' }
//每个角色对应的示例文本，切换角色自动填充到输入框
const form = reactive({ role: 'java', question: examples.java, audience: '入门', targetLanguage: '英语', productName: '降噪耳机' })
// 等待完整回答时禁止切换角色和重复提交。
const loading = ref(false)
// 只保存最近一次成功结果，切换角色时清空旧回答。
const result = ref(null)

/** 切换角色时替换示例输入，清空上一角色的回答。 */
function changeRole() {
  // 替换为当前角色的示例问题。
  form.question = examples[form.role]
  // 清空旧结果，只保存本次回答。
  result.value = null
}

/** 提交当前角色与变量；统一请求工具负责显示服务端错误。 */
async function send() {

  if (loading.value) return
  if (!form.question.trim()) return ElMessage.warning('请输入内容')
  if (form.role === 'copywriter' && !form.productName.trim()) return ElMessage.warning('商品名不能为空')
  loading.value = true
  result.value = null
  try {
    const data = { role: form.role, question: form.question }
    if (form.role === 'java') data.audience = form.audience
    if (form.role === 'translator') data.targetLanguage = form.targetLanguage
    if (form.role === 'copywriter') data.productName = form.productName
    
    const response = await request.post('/api/prompt/chat', data)
    
    if (response.code === '200') result.value = response.data
  } catch {
  } finally {
    loading.value = false
  }
}
// 将回答解析成 Markdown HTML，空内容使用空字符串。
const renderMarkdown = (text) => marked.parse(text || '')
</script>
<style scoped>
                
.prompt-chat-page {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.system-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 16px;
  background: #f4f7fa;
  border-radius: 6px;
  line-height: 1.8;
}
/* Markdown 正文样式。 */
.answer-content {
  /* 设置文字颜色。 */
  color: #374151;
  /* 设置正文字号。 */
  font-size: 14px;
  /* 设置正文行距。 */
  line-height: 1.75;
  /* 长文本允许换行。 */
  overflow-wrap: anywhere;
}
/* deep 使 scoped 样式作用于动态段落。 */
.answer-content :deep(p) {
  /* 段落上下间隔。 */
  margin: 6px 0;
}
/* 设置 Markdown 代码块。 */
.answer-content :deep(pre) {
  /* 长代码允许横向滚动。 */
  overflow-x: auto;
  /* 代码块内边距。 */
  padding: 10px 12px;
  /* 设置圆角。 */
  border-radius: 6px;
  /* 设置浅灰背景。 */
  background: #f0f2f5;
}
/* 代码使用等宽字体。 */
.answer-content :deep(code) {
  /* 优先使用常见等宽字体。 */
  font-family: Consolas, Menlo, monospace;
  /* 设置代码字号。 */
  font-size: 13px;
}
</style>

