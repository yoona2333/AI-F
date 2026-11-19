import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import ElementPlus from 'unplugin-element-plus/vite'

export default defineConfig({
  plugins: [
    vue(),
    ElementPlus({
      useSource: true,
    }),
    AutoImport({
      resolvers: [ElementPlusResolver({ importStyle: 'sass' })],
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'sass' })],
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        additionalData: `
          @use "@/assets/css/index.scss" as *;
        `,
      }
    }
  },
  server: {
    watch: {
      // Windows 下编辑器保存文件时先写临时文件再改名，chokidar 会撞上被占用的临时文件，
      // 抛出 EBUSY 直接让整个 dev server 退出。忽略这类中间产物即可避开。
      ignored: [
        '**/node_modules/**',
        '**/.git/**',
        '**/.*.tmpdir/**',
        '**/*.tmp',
        '**/.~*',
      ],
    },
  },
})
