<!-- 本文件提供同步对话页面：左侧提交问题和参数，右侧展示回答及本次参数。
     通过 request.js 请求后端，当前回答只保存在当前页面内存中。 -->
<!-- 模板定义页面结构，绑定的状态来自下面的 script setup。 -->
<template>
  <!-- 页面最外层容器，sync-chat-page 样式将内部两块区域排成两列。 -->
  <div class="sync-chat-page">
    
    <!-- 一个内容面板，content-panel 使用脚手架的公共卡片样式。 -->
    <section class="content-panel">
      <!-- 标题区域，公共样式安排标题与右侧操作按钮的位置。 -->
      <div class="section-heading">
        <!-- 将标题和说明组合为一个区域，便于与旁边操作项排列。 -->
        <div>
          <!-- 显示提问区标题。 -->
          <h3>向大模型提问</h3>
          <!-- 向用户说明当前页面采用完整返回的同步调用方式。 -->
          <p>同步调用：等模型生成完整回答后，一次性返回</p>
        </div>
      </div>
      <!-- 使用 Element Plus 表单；label-position=top 将字段标题放在控件上方。 -->
      <el-form label-position="top">
        
        <!-- 为问题输入框显示“问题”标题，并使用表单项间距。 -->
        <el-form-item label="问题"> 
          <!-- 使用 Element Plus 输入组件，下面的属性设置文本域和绑定值。
               双向绑定问题，输入会更新 form.question，代码赋值也会更新输入框。
               将输入组件显示为多行文本域。
               冒号表示绑定 JavaScript 数值，文本域初始显示 5 行。
               限制输入最多 2000 个字符，后端仍独立检查输入长度。
               开启字符计数显示，让用户看到输入长度。
               输入为空时显示提示文字，不会作为问题提交。 -->
          <el-input
            v-model="form.question"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            placeholder="输入你想问大模型的问题"
          />
        </el-form-item>
        
        
        <!-- 为温度控件显示名称与中文说明。 -->
        <el-form-item label="temperature（温度）">
          <!-- 绑定温度；范围为 0～1.9，步长 0.1；show-input 同时显示数值输入框。 -->
          <el-slider v-model="form.temperature" :min="0" :max="1.9" :step="0.1" show-input />
          <!-- 显示温度作用的辅助说明；参数只影响采样，不保证回答质量。 -->
          <div class="param-tip">越低回答越稳定，越高回答越发散、越有创意</div>
        </el-form-item>
        
        <!-- 为核采样控件显示名称与中文说明。 -->
        <el-form-item label="topP（核采样）">
          <!-- 绑定核采样值；范围为 0.1～1，步长 0.05，并显示数值输入框。 -->
          <el-slider v-model="form.topP" :min="0.1" :max="1" :step="0.05" show-input />
          <!-- 显示核采样作用的辅助说明。 -->
          <div class="param-tip">只从累计概率达到 topP 的候选词里挑选，越小选词越保守</div>
        </el-form-item>
        
        <!-- 为输出上限控件显示名称，单位是 Token。 -->
        <el-form-item label="maxTokens（最大输出 Token 数）">
          <!-- 绑定整数上限；范围为 1～4096，增减按钮步长为 64，也可以直接输入 20。 -->
          <el-input-number v-model="form.maxTokens" :min="1" :max="4096" :step="64" />
          <!-- 显示输出上限的验证提示；实际按 Token 数限制，不按汉字数。 -->
          <div class="param-tip">回答达到这个长度会被截断，可以设成 20 试试效果</div>
        </el-form-item>
        
        <!-- 把发送和恢复参数按钮排列在同一区域。 -->
        <div class="form-actions">
          <!-- 主按钮点击调用 sendQuestion；loading 为 true 时显示加载状态并阻止再次点击该按钮。 -->
          <el-button type="primary" :loading="loading" @click="sendQuestion">发送</el-button>
          <!-- 点击调用 resetParams，只恢复三个参数，保留问题。 -->
          <el-button @click="resetParams">恢复默认参数</el-button>
        </div>
      </el-form>
    </section>
    
    <!-- 一个内容面板，content-panel 使用脚手架的公共卡片样式。 -->
    <section class="content-panel">
      <!-- 标题区域，公共样式安排标题与右侧操作按钮的位置。 -->
      <div class="section-heading">
        <!-- 将标题和说明组合为一个区域，便于与旁边操作项排列。 -->
        <div>
          <!-- 显示右侧回答区标题。 -->
          <h3>本次回答</h3>
          <!-- 说明结果中包含本次调用的参数。 -->
          <p>展示当前回答和本次使用的模型参数</p>
        </div>
      </div>
      
      <!-- 只有 loading 为 true 时创建等待提示区域。 -->
      <div v-if="loading" class="waiting-card">
        <!-- 等待期间显示固定说明，不是模型正在生成的回答片段。 -->
        大模型正在生成回答，同步调用需要等全部内容生成完才会返回……
      </div>
      <!-- 没有结果且没有请求在等待时，显示 Element Plus 空状态说明。 -->
      <el-empty v-if="!result && !loading" description="还没有回答，先在左侧提一个问题吧" />

      <!-- 当前结果不为空时显示回答卡片；模板自动解包 ref，无需写 .value。 -->
      <div v-if="result" class="answer-card">
        <!-- 插值显示本次结果保存的问题。 -->
        <div class="answer-question">问：{{ result.question }}</div>
        
        <!-- 容纳本次结果的模型、参数和结束状态标签。 -->
        <div class="answer-meta">
          <!-- 用描边标签显示模型名称，effect=plain 指定标签外观。 -->
          <el-tag effect="plain">{{ result.modelName }}</el-tag>
          <!-- 信息色标签显示本次结果的温度。 -->
          <el-tag effect="plain" type="info">temperature {{ result.temperature }}</el-tag>
          <!-- 信息色标签显示本次结果的核采样值。 -->
          <el-tag effect="plain" type="info">topP {{ result.topP }}</el-tag>
          <!-- 信息色标签显示本次结果的输出上限。 -->
          <el-tag effect="plain" type="info">maxTokens {{ result.maxTokens }}</el-tag>
          
          <!-- v-if：结束原因等于 LENGTH 时显示警告色标签；紧邻的 v-else：其他情况显示成功色标签。
          当前代码未单独展示 UNKNOWN。 -->
          <el-tag v-if="result.finishReason === 'LENGTH'" type="warning">被截断（达到 maxTokens）</el-tag>
          <el-tag v-else type="success">正常结束</el-tag>
        </div>
        
        <!-- 调用 renderMarkdown 转换回答，通过 v-html 插入 HTML；class 控制正文样式。 -->
        <div class="answer-content" v-html="renderMarkdown(result.answer)"></div>
      </div>
    </section>
  </div>
</template>
<!-- setup 中的变量和函数可以直接用于模板，不需要写 return 暴露。 -->
<script setup>
// reactive 创建响应式对象；ref 保存单个响应式值，脚本中通过 .value 读写。
import { reactive, ref } from 'vue'
// 导入消息提示组件，在问题为空时给用户显示提示。
import { ElMessage } from 'element-plus'
// 导入 Markdown 解析器，将回答中的 Markdown 转换为 HTML。
import { marked } from 'marked'
// 导入 axios 封装，使用已配置的后端地址、请求超时和错误拦截器。
import request from '@/utils/request.js'

// 页面默认参数：温度 0.7、核采样 0.8、输出上限 1024；初始化和恢复操作共用。
const DEFAULT_PARAMS = { temperature: 0.7, topP: 0.8, maxTokens: 1024 }


// 创建表单响应式对象，字段变化后，绑定的输入框和参数控件同步更新。
const form = reactive({
  // 问题初始为空，用户输入后发送。
  question: '',
  // 展开默认对象，将 temperature、topP、maxTokens 加入表单。
  ...DEFAULT_PARAMS,
})

// 等待状态初始为 false；发请求时设为 true，控制按钮加载和等待提示。
const loading = ref(false)

// 当前结果初始为空，只保存本次回答；重新发送时清空。
const result = ref(null)

// 发送函数，无输入参数，读取 form；异步等待接口返回后保存结果。
// 失败提示由请求拦截器负责，finally 统一关闭加载状态。
const sendQuestion = async () => {

  // 去掉首尾空白后判断问题是否为空，为空则停止发送。
  if (!form.question.trim()) {
    // 弹出非空提示，让用户补充问题再发送。
    ElMessage.warning('请先输入问题')
    // 立即结束当前函数，不进入下面的网络请求。
    return
  }

  // 请求仍在等待时直接返回，避免重复提交。
  if (loading.value) return

  // 复制发送时的问题和参数，避免等待期间修改表单影响结果展示。
  const payload = { ...form }
  // 清掉上次回答，右侧只展示本次请求的状态。
  result.value = null
  // 开启等待状态，按钮显示加载动画，右侧出现等待提示。
  loading.value = true
  // 开始异常处理范围，网络调用失败时进入 catch。
  try {

    // 提交发送时保存的 JSON 参数；await 等待后端返回业务响应。
    const res = await request.post('/api/chat/sync', payload)

    // 检查字符串业务码，只有成功时才保存结果；HTTP 200 本身不能代替这个判断。
    if (res.code === '200') {

      // 返回数据包含回答、模型名、参数和结束原因；本次结果直接替换旧结果。
      result.value = { question: payload.question, ...res.data }
    }
  // 接住请求异常；request.js 已显示错误提示，这里不重复弹窗。
  } catch {

  // 不论成功、业务失败还是网络异常，最后都执行下面的清理操作。
  } finally {
    // 关闭等待状态，让用户可以继续操作，隐藏等待提示。
    loading.value = false
  }
}

// 恢复参数函数，无输入和返回值，仅重置三个参数，保留当前问题。
const resetParams = () => {

  // 把默认值复制到现有响应式对象；保持引用，且不会覆盖 question。
  Object.assign(form, DEFAULT_PARAMS)
}

// 接收回答字符串，空值用空字符串兜底，返回 Markdown 转换后的 HTML。
// 当前直接渲染返回内容；此函数没有实现 HTML 安全过滤。
const renderMarkdown = (text) => marked.parse(text || '')
</script>
<!-- scoped 将样式限制在本组件；动态 HTML 的内部元素使用 :deep() 设置样式。 -->
<style scoped>

/* 页面两列布局，对应模板最外层容器。 */
.sync-chat-page {
  /* 采用网格布局，把提问区和回答区排成两列。 */
  display: grid;
  /* 左列固定 420px；右列使用剩余空间，最小宽度允许收缩到 0。 */
  grid-template-columns: 420px minmax(0, 1fr);
  /* 两列间隔 16px，使左右内容区分开。 */
  gap: 16px;
  /* 网格内容靠上对齐，不强制两块内容高度一致。 */
  align-items: start;
}

/* 设置参数输入框下方的说明文字。 */
.param-tip {
  /* 参数提示占满当前表单项宽度。 */
  width: 100%;
  /* 参数提示使用浅灰色，和输入控件区分。 */
  color: #9aa2af;
  /* 参数提示字号为 12px，保持辅助信息的视觉层级。 */
  font-size: 12px;
  /* 行高为字号的 1.6 倍，提高多行参数说明的可读性。 */
  line-height: 1.6;
}

/* 设置发送与恢复按钮的排列方式。 */
.form-actions {
  /* 将子元素按弹性布局排列，适合按钮和参数标签横向展示。 */
  display: flex;
  /* 相邻按钮或操作项间隔 8px。 */
  gap: 8px;
}

/* 设置等待回答时显示的提示区域。 */
.waiting-card {
  /* 与下一块内容留出 12px 垂直间隔。 */
  margin-bottom: 12px;
  /* 内容上下留白 14px、左右留白 16px，避免文字紧贴边框。 */
  padding: 14px 16px;
  /* 等待提示文字使用蓝色，突出当前请求状态。 */
  color: #2e5fa7;
  /* 使用 13px 字号，适合辅助文字或代码内容。 */
  font-size: 13px;
  /* 给等待提示加 1px 蓝色虚线边框。 */
  border: 1px dashed #9cb8e2;
  /* 将卡片或代码块边角设置为 6px 圆角。 */
  border-radius: 6px;
  /* 等待提示使用浅蓝背景。 */
  background: #f3f7fd;
}

/* 设置当前回答的边框、间隔和背景。 */
.answer-card {
  /* 与下一块内容留出 12px 垂直间隔。 */
  margin-bottom: 12px;
  /* 内容上下留白 14px、左右留白 16px，避免文字紧贴边框。 */
  padding: 14px 16px;
  /* 回答卡片使用浅灰实线边框，与相邻记录分开。 */
  border: 1px solid #e2e6ec;
  /* 将卡片或代码块边角设置为 6px 圆角。 */
  border-radius: 6px;
  /* 回答卡片使用接近白色的背景。 */
  background: #fafbfc;
}

/* 设置回答顶部的用户问题文字。 */
.answer-question {
  /* 问题文字使用深色，突出本次回答的问题。 */
  color: #111827;
  /* 使用 14px 字号展示问题或回答正文。 */
  font-size: 14px;
  /* 问题文字适度加粗，方便区分问题与回答。 */
  font-weight: 600;
}

/* 设置模型名、参数和结束状态标签的布局。 */
.answer-meta {
  /* 将子元素按弹性布局排列，适合按钮和参数标签横向展示。 */
  display: flex;
  /* 空间不足时允许换行，避免按钮或标签撑出容器。 */
  flex-wrap: wrap;
  /* 模型名和参数标签间隔 6px。 */
  gap: 6px;
  /* 标签区域上下间隔 10px，左右不额外留白。 */
  margin: 10px 0;
}

/* 设置回答正文的字体颜色与行距。 */
.answer-content {
  /* 回答正文使用深灰色，保证长文本清晰可读。 */
  color: #374151;
  /* 使用 14px 字号展示问题或回答正文。 */
  font-size: 14px;
  /* 正文行高为字号的 1.75 倍，方便阅读多行回答。 */
  line-height: 1.75;
}

/* 穿透 scoped 作用域，设置 v-html 动态生成的段落。 */
.answer-content :deep(p) {
  /* Markdown 段落上下间隔 6px，左右不留外边距。 */
  margin: 6px 0;
}

/* 穿透 scoped 作用域，设置动态生成的 Markdown 代码块。 */
.answer-content :deep(pre) {
  /* 代码过长时允许横向滚动，避免撑宽回答区域。 */
  overflow-x: auto;
  /* 代码块上下留白 10px，左右留白 12px。 */
  padding: 10px 12px;
  /* 将卡片或代码块边角设置为 6px 圆角。 */
  border-radius: 6px;
  /* 代码块使用浅灰背景，与普通回答文本区分。 */
  background: #f0f2f5;
}

/* 穿透 scoped 作用域，设置动态生成的行内代码和代码块字体。 */
.answer-content :deep(code) {
  /* 代码优先使用等宽字体，保持字符和缩进对齐。 */
  font-family: Consolas, Menlo, monospace;
  /* 使用 13px 字号，适合辅助文字或代码内容。 */
  font-size: 13px;
}
</style>

