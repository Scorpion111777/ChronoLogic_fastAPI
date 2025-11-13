import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from '../frontend/App.vue'
import router from '../frontend/router/index.js'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
