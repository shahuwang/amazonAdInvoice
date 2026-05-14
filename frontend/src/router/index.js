import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import ReportView from '../views/ReportView.vue'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', component: UploadView },
  { path: '/report', component: ReportView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
