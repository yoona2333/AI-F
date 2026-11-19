<template>
  <div class="app-shell">
    <aside class="sidebar">
      <router-link class="brand" to="/">
        <span class="brand-mark">AI</span>
        <span class="brand-text">
          <strong>大模型应用开发</strong>
          <em>MODEL TEST BENCH</em>
        </span>
      </router-link>

      <el-scrollbar class="lesson-nav">
        <div class="nav-label">目录</div>
        <el-menu :default-active="route.path" router>
          <el-menu-item class="nav-home" index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>首页</span>
          </el-menu-item>

          <el-sub-menu
            v-for="chapter in lessonMenus"
            :key="chapter.chapter"
            :index="`chapter-${chapter.chapter}`"
          >
            <template #title>
              <span class="chapter-no">{{ pad(chapter.chapter) }}</span>
              <span class="chapter-title">{{ chapter.title }}</span>
            </template>

            <el-menu-item v-for="lesson in chapter.lessons" :key="lesson.path" :index="lesson.path">
              {{ lesson.chapter }}-{{ lesson.section }} {{ lesson.title }}
            </el-menu-item>

           
            <el-menu-item
              v-if="!chapter.lessons.length"
              :index="`pending-${chapter.chapter}`"
              disabled
              class="nav-pending"
            >
              
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-foot">
        <span>{{ lessonMenus.length }} 章</span>
        <span>·</span>
        <span>{{ lessonTotal }} 个练习</span>
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="topbar-title">
          <span class="topbar-index">{{ pageIndex }}</span>
          <h1>{{ pageTitle }}</h1>
        </div>

        <div class="topbar-meta">
          <template v-for="(part, index) in stackParts" :key="part">
            <span v-if="index > 0" class="stack-sep">·</span>
            <span class="stack-chip">{{ part }}</span>
          </template>
        </div>
      </header>

      <section class="page-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { HomeFilled } from '@element-plus/icons-vue'
import { lessonMenus } from '@/router/lessonRegistry.js'

const route = useRoute()

// 技术栈标签形如「Python 3.12 · FastAPI」，拆成两枚等宽标记
const stackParts = (import.meta.env.VITE_STACK_LABEL || '').split('·').map(part => part.trim())

const lessonTotal = lessonMenus.reduce((total, chapter) => total + chapter.lessons.length, 0)

// 编号补零，让 1 与 10 在等宽字体下宽度一致
const pad = value => String(value).padStart(2, '0')

// 顶栏左侧编号：课程页显示「章 / 节」，首页显示 INDEX
const pageIndex = computed(() => {
  const { chapter, section } = route.meta
  return chapter ? `${pad(chapter)} / ${pad(section)}` : 'INDEX'
})

// 顶栏标题去掉路由里重复的「1-1」前缀，避免编号出现两次
const pageTitle = computed(() => {
  const title = route.meta.title || '课程首页'
  return title.replace(/^\d+-\d+\s+/, '')
})
</script>
