<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth.js'
import { useLocaleStore } from '../stores/locale.js'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const { t, toggleLocale } = localeStore
const { isEN } = storeToRefs(localeStore)

const isLogin = computed(() => route.name === 'login')
const name = ref('')
const email = ref('')
const password = ref('')
const passwordConfirm = ref('')
const error = ref('')
const loading = ref(false)
const showPass = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  await new Promise(r => setTimeout(r, 300))

  if (isLogin.value) {
    const res = authStore.login(email.value, password.value)
    if (!res.success) { error.value = res.error; loading.value = false; return }
  } else {
    if (!name.value.trim()) { error.value = t('auth.nameError'); loading.value = false; return }
    if (password.value !== passwordConfirm.value) { error.value = t('auth.passwordMismatch'); loading.value = false; return }
    const res = authStore.register(name.value, email.value, password.value)
    if (!res.success) { error.value = res.error; loading.value = false; return }
  }

  loading.value = false
  router.push('/operations')
}

const authErrorText = computed(() => {
  if (!error.value) return ''
  if (error.value === 'Користувач з таким email вже існує') return t('auth.userExists')
  if (error.value === 'Пароль має бути не менше 6 символів') return t('auth.passwordShort')
  if (error.value === 'Невірний email або пароль') return t('auth.invalidCredentials')
  return error.value
})
</script>

<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="auth-orb auth-orb--1"></div>
      <div class="auth-orb auth-orb--2"></div>
      <div class="auth-grid"></div>
    </div>

    <div class="auth-card">
      <div class="auth-top-row">
        <button @click="router.push('/')" class="back-link">{{ t('nav.back') }}</button>
        <button class="lang-toggle" @click="toggleLocale" :title="isEN ? 'Українська' : 'English'">
          {{ isEN ? 'UA' : 'EN' }}
        </button>
      </div>

      <div class="auth-logo-wrap">
        <img src="../assets/icons/logo.svg" alt="ChronoLogic" class="auth-logo" />
      </div>

      <h1 class="auth-title">{{ isLogin ? t('auth.loginTitle') : t('auth.registerTitle') }}</h1>
      <p class="auth-sub">
        {{ isLogin ? t('auth.loginSub') : t('auth.registerSub') }}
      </p>

      <form @submit.prevent="submit" class="auth-form">
        <div v-if="!isLogin" class="form-field">
          <label>{{ t('auth.nameLabel') }}</label>
          <input v-model="name" type="text" :placeholder="t('auth.namePlaceholder')" class="auth-input" required />
        </div>

        <div class="form-field">
          <label>Email</label>
          <input v-model="email" type="email" :placeholder="t('auth.emailPlaceholder')" class="auth-input" required />
        </div>

        <div class="form-field">
          <label>{{ t('auth.passwordLabel') }}</label>
          <div class="input-with-action">
            <input v-model="password" :type="showPass ? 'text' : 'password'"
                   :placeholder="t('auth.passwordPlaceholder')" class="auth-input" required />
            <button type="button" @click="showPass = !showPass" class="show-pass-btn">
              {{ showPass ? '🙈' : '👁' }}
            </button>
          </div>
        </div>

        <div v-if="!isLogin" class="form-field">
          <label>{{ t('auth.confirmLabel') }}</label>
          <input v-model="passwordConfirm" :type="showPass ? 'text' : 'password'"
                 :placeholder="t('auth.confirmPlaceholder')" class="auth-input" required />
        </div>

        <p v-if="authErrorText" class="auth-error">{{ authErrorText }}</p>

        <button type="submit" class="auth-submit" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>{{ isLogin ? t('auth.loginBtn') : t('auth.registerBtn') }}</span>
        </button>
      </form>

      <div class="auth-switch">
        <template v-if="isLogin">
          {{ t('auth.noAccount') }}
          <button @click="router.push('/register')" class="switch-link">{{ t('auth.registerLink') }}</button>
        </template>
        <template v-else>
          {{ t('auth.hasAccount') }}
          <button @click="router.push('/login')" class="switch-link">{{ t('auth.loginLink') }}</button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

.auth-page {
  font-family: 'Outfit', sans-serif;
  min-height: 100vh;
  background: #0a0a14;
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
  position: relative; overflow: hidden;
}
.auth-bg {
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
}
.auth-orb {
  position: absolute; border-radius: 50%;
  filter: blur(80px); opacity: 0.15;
}
.auth-orb--1 { width: 500px; height: 500px; background: #5047e5; top: -150px; left: -100px; }
.auth-orb--2 { width: 400px; height: 400px; background: #8b3ab3; bottom: -100px; right: -100px; }
.auth-grid {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}

.auth-card {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px;
  padding: 40px;
  width: 100%;
  max-width: 440px;
  position: relative; z-index: 1;
  backdrop-filter: blur(16px);
  box-shadow: 0 24px 80px rgba(0,0,0,0.5);
}

.auth-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.lang-toggle {
  padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2);
  background: transparent; color: #a0a8ff; font-weight: 700; font-size: 13px;
  cursor: pointer; transition: all .2s; font-family: 'Outfit', sans-serif;
  letter-spacing: .5px;
}
.lang-toggle:hover {
  background: rgba(80,71,229,0.3);
  color: #fff;
}

.back-link {
  display: inline-block;
  background: none; border: none; color: #7070a0;
  font-size: 13px; cursor: pointer; padding: 0;
  font-family: 'Outfit', sans-serif;
  transition: color 0.2s;
}
.back-link:hover { color: #a0a0cc; }

.auth-logo-wrap { text-align: center; margin-bottom: 24px; }
.auth-logo { height: 44px; filter: brightness(1.1); }

.auth-title {
  font-size: 26px; font-weight: 800; color: #f0f0f8;
  text-align: center; margin: 0 0 6px;
}
.auth-sub {
  text-align: center; color: #666688; font-size: 14px; margin: 0 0 28px;
}

.auth-form { display: flex; flex-direction: column; gap: 16px; }

.form-field { display: flex; flex-direction: column; gap: 6px; }
.form-field label { font-size: 13px; font-weight: 600; color: #9090b0; }

.auth-input {
  padding: 13px 16px;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 11px; color: #f0f0f8;
  font-size: 15px; font-family: 'Outfit', sans-serif;
  transition: all 0.2s; width: 100%; box-sizing: border-box;
}
.auth-input::placeholder { color: #444466; }
.auth-input:focus {
  outline: none;
  border-color: rgba(80,71,229,0.6);
  background: rgba(80,71,229,0.08);
  box-shadow: 0 0 0 3px rgba(80,71,229,0.15);
}

.input-with-action { position: relative; }
.input-with-action .auth-input { padding-right: 48px; }
.show-pass-btn {
  position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer; font-size: 16px; padding: 4px;
}

.auth-error {
  margin: 0; padding: 12px 16px;
  background: rgba(220,50,50,0.1); border: 1px solid rgba(220,50,50,0.25);
  border-radius: 8px; color: #ff7070; font-size: 13px;
}

.auth-submit {
  padding: 14px; border-radius: 12px; border: none;
  background: linear-gradient(135deg, #5047e5, #8b3ab3);
  color: #fff; font-size: 16px; font-weight: 700; cursor: pointer;
  font-family: 'Outfit', sans-serif;
  transition: all 0.2s; margin-top: 4px;
  box-shadow: 0 0 30px rgba(80,71,229,0.35);
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.auth-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 0 45px rgba(80,71,229,0.5); }
.auth-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner {
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.auth-switch {
  text-align: center; margin-top: 20px;
  font-size: 14px; color: #555577;
}
.switch-link {
  background: none; border: none; color: #7b8cff;
  font-size: 14px; cursor: pointer; font-weight: 600;
  font-family: 'Outfit', sans-serif;
  text-decoration: underline; margin-left: 4px;
}
.switch-link:hover { color: #a0b0ff; }
</style>
