import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/views/AppLayout.vue'
import Home from '@/views/Home.vue'
import NotFound from '@/views/NotFound.vue'
import { lessonRoutes } from '@/router/lessonRegistry.js'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', name: 'home', component: Home, meta: { title: '课程首页' } },
        ...lessonRoutes,
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFound },
  ],
})

router.afterEach(() => {
  document.title = 'AI大模型应用开发全家桶-武哥'
  window.scrollTo({ top: 0, behavior: 'smooth' })
})

export default router
