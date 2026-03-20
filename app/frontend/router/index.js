import { createRouter, createWebHistory } from 'vue-router'
import LandingView from '../views/LandingView.vue'
import AuthView from '../views/AuthView.vue'
import OperationsView from '../views/OperationsView.vue'
import ProfileOperations from '../views/ProfileOperations.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: LandingView },
    { path: '/login', name: 'login', component: AuthView },
    { path: '/register', name: 'register', component: AuthView },
    { path: '/operations', name: 'operations', component: OperationsView, meta: { requiresAuth: true } },
    { path: '/profileOper', name: 'profileOperations', component: ProfileOperations, meta: { requiresAuth: true } },
  ]
})

// Auth guard
router.beforeEach((to) => {
  if (to.meta.requiresAuth) {
    const session = localStorage.getItem('chronologic_session')
    if (!session) return { name: 'login' }
  }
})

export default router
