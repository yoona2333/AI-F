<template>
  <div class="app-shell">
    <aside class="sidebar">
      <router-link class="brand" to="/">
        <span>
          <strong>AI 大模型应用开发全家桶</strong>
        </span>
      </router-link>

      <el-scrollbar class="lesson-nav">
        <el-menu :default-active="route.path" router>
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>课程首页</span>
          </el-menu-item>
          <el-sub-menu v-for="chapter in lessonMenus" :key="chapter.chapter" :index="`chapter-${chapter.chapter}`">
            <template #title>
              <el-icon><Collection /></el-icon>
              <span>{{ chapter.title }}</span>
            </template>
            <el-menu-item v-for="lesson in chapter.lessons" :key="lesson.path" :index="lesson.path">
              {{ lesson.chapter }}-{{ lesson.section }} {{ lesson.title }}
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div>
          <h1>{{ route.meta.title || 'AI 大模型应用开发' }}</h1>
        </div>
        <el-tag effect="plain" type="success">{{ stackLabel }}</el-tag>
      </header>
      <section class="page-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { Collection, HomeFilled } from '@element-plus/icons-vue'
import { lessonMenus } from '@/router/lessonRegistry.js'

const route = useRoute()
const stackLabel = import.meta.env.VITE_STACK_LABEL
</script>
