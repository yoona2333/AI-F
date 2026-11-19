<template>
  <div class="home-page">
    <section class="intro-panel">
      <h2>AI 大模型应用开发全家桶</h2>
      <p>
        使用 {{ backendName }} 从零学习大模型应用开发，通过可以直接运行的示例，依次掌握基础调用、RAG、工作流、Agent 与 MCP。
      </p>
      <div class="course-route" aria-label="课程学习路线">
        <template v-for="(item, index) in courseRoute" :key="item">
          <span>{{ item }}</span>
          <i v-if="index < courseRoute.length - 1">→</i>
        </template>
      </div>
    </section>

    <section class="content-panel">
      <div class="section-heading">
        <div>
          <h3>技术栈与学习路线</h3>
          <p>当前项目使用的核心技术及其在课程中的作用。</p>
        </div>
        <el-tag effect="plain">{{ courseEdition }}</el-tag>
      </div>

      <div class="table-wrap">
        <table class="tech-table">
          <thead>
            <tr>
              <th>层级</th>
              <th>技术选型</th>
              <th>版本</th>
              <th>课程用途</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in techStack" :key="item.name">
              <td>{{ item.layer }}</td>
              <td class="tech-name">{{ item.name }}</td>
              <td><code>{{ item.version }}</code></td>
              <td>{{ item.purpose }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="info-grid">
      <section class="content-panel">
        <div class="section-heading">
          <div>
            <h3>关于作者</h3>
            <p>课程内容与示例代码由作者持续维护。</p>
          </div>
        </div>
        <div class="author-info">
          <div class="author-avatar">武</div>
          <div>
            <strong>武哥聊编程</strong>
            <p>专注 Java、Python 与 AI 大模型应用开发，持续分享从技术入门到项目落地的实战内容。</p>
            <span>AIGC编程网</span>
          </div>
        </div>
      </section>

      <section class="content-panel practice-panel">
        <div class="section-heading">
          <div>
            <h3>进一步学习</h3>
            <p>AIGC编程网 · AI 实战库</p>
          </div>
        </div>
        <p class="practice-copy">
          本课程用于建立完整的技术认知和入门能力。如果你希望继续学习真实业务场景、工程化设计和企业级项目，可以进入 AI 实战库。
        </p>
        <a
          class="practice-link"
          href="https://aigcbaba.com/ai-project"
          target="_blank"
          rel="noopener noreferrer"
        >
          查看 AI 实战库
          <span>→</span>
        </a>
      </section>
    </div>
  </div>
</template>

<script setup>
const courseEdition = import.meta.env.VITE_COURSE_EDITION
const backendName = import.meta.env.VITE_BACKEND_NAME
const isSpringBoot = backendName === 'Spring Boot'

const courseRoute = ['大模型基础', 'Tool Calling', 'RAG 检索', '工作流', 'Agent', 'MCP']

const commonStack = [
  { layer: '前端', name: 'Vue', version: '3.5.43', purpose: '课程页面与交互实现' },
  { layer: 'UI', name: 'Element Plus', version: '2.14.6', purpose: '基础界面组件' },
  { layer: '工程化', name: 'Vite', version: '8.3.0', purpose: '前端开发与构建' },
]

const javaStack = [
  { layer: '运行环境', name: 'Java', version: '21.0.5 LTS', purpose: 'Java 课程运行环境' },
  { layer: 'Web 框架', name: 'Spring Boot', version: '4.1.1', purpose: '接口、配置、SSE 与文件处理' },
  { layer: '大模型应用', name: 'LangChain4j', version: '1.20.0', purpose: '模型调用、Prompt、工具与 RAG' },
  { layer: '工作流', name: 'LangGraph4j', version: '1.9.1', purpose: '状态图与 Agent 流程编排' },
  { layer: 'MCP', name: 'MCP Java SDK', version: '2.0.1', purpose: 'MCP Server 与 Client' },
]

const pythonStack = [
  { layer: '运行环境', name: 'Python', version: '3.12.10', purpose: 'Python 课程运行环境' },
  { layer: 'Web 框架', name: 'FastAPI', version: '0.141.1', purpose: '接口、配置、SSE 与文件处理' },
  { layer: '大模型应用', name: 'LangChain', version: '1.4.2', purpose: '模型调用、Prompt、工具与 RAG' },
  { layer: '工作流', name: 'LangGraph', version: '1.2.12', purpose: '状态图与 Agent 流程编排' },
  { layer: 'MCP', name: 'FastMCP', version: '4.0.8', purpose: 'MCP Server 与 Client' },
]

const techStack = [...(isSpringBoot ? javaStack : pythonStack), ...commonStack]
</script>
