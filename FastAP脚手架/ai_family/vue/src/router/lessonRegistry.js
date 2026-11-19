const lessonComponents = import.meta.glob('../views/lesson/*.vue')

const courseChapters = [
  { chapter: 1, title: '大模型应用基础' },
  { chapter: 2, title: 'Tool Calling' },
  { chapter: 3, title: 'RAG知识库' },
  { chapter: 4, title: 'AI 工作流' },
  { chapter: 5, title: 'Agent' },
  { chapter: 6, title: 'MCP' },
]

const lessons = Object.entries(lessonComponents)
  .map(([filePath, component]) => {
    const fileName = filePath.split('/').pop()
    // 兼容两种写法：L1_1_标题.vue（推荐）和 1-1 标题.vue / 1_1_标题.vue。
    const match = fileName.match(/^L?(\d+)[-_.](\d+)[-_.\s]*(.+)\.vue$/)
    // 不符合规范的文件只跳过并告警，避免一个文件名写错就让整个站点白屏。
    if (!match) {
      console.warn(`已跳过无法识别章节/小节的文件：${filePath}（请用 L1_1_标题.vue 或 1-1 标题.vue）`)
      return null
    }

    const chapter = Number(match[1])
    const section = Number(match[2])
    return {
      chapter,
      section,
      title: match[3].replaceAll('_', ' '),
      path: `/lesson/${chapter}-${section}`,
      name: `lesson-${chapter}-${section}`,
      component,
    }
  })
  .filter(Boolean)
  .sort((left, right) => left.chapter - right.chapter || left.section - right.section)

export const lessonRoutes = lessons.map(lesson => ({
  path: lesson.path.slice(1),
  name: lesson.name,
  component: lesson.component,
  meta: {
    title: `${lesson.chapter}-${lesson.section} ${lesson.title}`,
    chapter: lesson.chapter,
    section: lesson.section,
  },
}))

export const lessonMenus = courseChapters.map(chapter => ({
  ...chapter,
  lessons: lessons.filter(lesson => lesson.chapter === chapter.chapter),
}))
