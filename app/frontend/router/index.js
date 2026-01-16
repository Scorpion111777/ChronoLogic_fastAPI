import { createRouter, createWebHistory } from 'vue-router'
import OperationsView from '../views/OperationsView.vue'
import ProfileOperations from '../views/ProfileOperations.vue'
import 'bootstrap/dist/css/bootstrap.min.css';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: OperationsView
    },
    {
      path: '/operations',
      name: 'operations',
      component: OperationsView
    },
    {
      path: '/profileOper',
      name: 'profileOperations',
      component: ProfileOperations
    }
  ]
})

export default router
