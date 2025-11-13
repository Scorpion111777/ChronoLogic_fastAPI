import { createRouter, createWebHistory } from 'vue-router'
import OperationsView from '../views/OperationsView.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: OperationsView
    },
    // 2. Додаємо шлях для вашої сторінки
    {
      path: '/operations',
      name: 'operations',
      component: OperationsView
    }
  ]
})

export default router
