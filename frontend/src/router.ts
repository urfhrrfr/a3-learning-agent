import { createRouter, createWebHistory } from 'vue-router'
import Workspace from './pages/Workspace.vue'
import Profile from './pages/Profile.vue'
import Generate from './pages/Generate.vue'
import Resources from './pages/Resources.vue'
import Path from './pages/Path.vue'
import Tutor from './pages/Tutor.vue'
import Assessment from './pages/Assessment.vue'
import Auth from './pages/Auth.vue'
import { authToken } from './api'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/auth', component: Auth, meta: { public: true } },
    { path: '/', component: Workspace },
    { path: '/profile', component: Profile },
    { path: '/generate', component: Generate },
    { path: '/resources', component: Resources },
    { path: '/path', component: Path },
    { path: '/tutor', component: Tutor },
    { path: '/assessment', component: Assessment }
  ]
})

router.beforeEach((to) => {
  if (!to.meta.public && !authToken()) {
    return { path: '/auth', query: { redirect: to.fullPath } }
  }
  if (to.path === '/auth' && authToken()) {
    return '/'
  }
})
