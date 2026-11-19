<template>
  <div class="home-page">
    <section class="hero">
      <div class="hero-main">
        <span class="eyebrow">{{ courseEdition }}</span>
        <h1></h1>
        <p class="hero-lede">
          从一次同步对话开始，逐章加上工具调用、检索、流程编排与 Agent，
          最后用 MCP 把能力交给其他系统。每一步都有可以直接运行的练习。
        </p>
        <router-link v-if="firstLesson" class="hero-cta" :to="firstLesson.path">
          从 {{ firstLesson.chapter }}-{{ firstLesson.section }} 开始
          <span class="arrow">→</span>
        </router-link>
      </div>

      <nav class="hero-route" aria-label="学习路线">
        <div class="route-head">
          <span class="eyebrow">学习路线</span>
        </div>
        <ol class="route">
          <li v-for="chapter in lessonMenus" :key="chapter.chapter">
            <span class="no">{{ pad(chapter.chapter) }}</span>
            <span class="name">{{ chapter.title }}</span>
            <span class="state mono" :class="{ pending: !chapter.lessons.length }">
              {{ chapter.lessons.length ? `${chapter.lessons.length} 节` : '待更新' }}
            </span>
          </li>
        </ol>
      </nav>
    </section>

    <section class="datasheet">
      <header class="datasheet-head">
        <div>
          <span class="eyebrow">技术栈</span>
          <h2></h2>
        </div>
        <span class="datasheet-count">{{ techStack.length }} 项依赖</span>
      </header>

      <table class="tech-table">
        <thead>
          <tr>
            <th class="col-layer">Layer</th>
            <th class="col-name">Tech</th>
            <th class="col-version">Version</th>
            <th class="col-purpose">Purpose</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in techStack" :key="item.name">
            <td class="col-layer">{{ item.layer }}</td>
            <td class="col-name">{{ item.name }}</td>
            <td class="col-version"><code>{{ item.version }}</code></td>
            <td class="col-purpose">{{ item.purpose }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { lessonMenus } from '@/router/lessonRegistry.js'

const courseEdition = import.meta.env.VITE_COURSE_EDITION
const backendName = import.meta.env.VITE_BACKEND_NAME
const isSpringBoot = backendName === 'Spring Boot'

// 编号补零，让 01 与 10 在等宽字体下等宽
const pad = value => String(value).padStart(2, '0')

// 首页主按钮直接指向第一个可进入的练习，没有练习时不渲染按钮
const firstLesson = computed(() => lessonMenus.flatMap(chapter => chapter.lessons)[0] || null)

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
