<template>
  <div class="not-found">
    <div class="not-found-inner">
      <span class="mono code">404</span>
      <h1>这一节还没排上</h1>
      <p>链接可能已经调整过，或者对应的课程内容还没发布。</p>
      <router-link class="back" to="/">回到课程首页</router-link>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: grid;
  min-height: 100vh;
  padding: 24px;
  place-items: center;
  background: var(--paper);
}

.not-found-inner {
  max-width: 30em;
  text-align: center;
}

/* 大号等宽编号，作为页面的唯一视觉重心 */
.code {
  display: block;
  color: var(--signal);
  font-size: 64px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.04em;
}

.not-found h1 {
  margin: 20px 0 0;
  color: var(--ink);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.not-found p {
  margin: 10px 0 0;
  color: var(--ink-3);
  font-size: 13px;
  line-height: 1.7;
}

.back {
  display: inline-flex;
  align-items: center;
  margin-top: 26px;
  padding: 10px 18px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  background: var(--brand-2);
  border-radius: var(--radius);
  transition: background 0.15s ease;
}

.back:hover {
  background: var(--brand-3);
}
</style>
