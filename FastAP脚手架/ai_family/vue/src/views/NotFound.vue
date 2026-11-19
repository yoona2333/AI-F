<template>
  <el-result icon="warning" title="页面不存在" sub-title="这个课节可能还没有创建">
    <template #extra>
      <el-button type="primary" @click="$router.push('/')">返回课程首页</el-button>
    </template>
  </el-result>
</template>
