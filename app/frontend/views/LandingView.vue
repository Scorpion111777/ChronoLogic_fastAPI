<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useLocaleStore } from '../stores/locale.js'

const router = useRouter()
const authStore = useAuthStore()
const { t, toggleLocale, isEN } = useLocaleStore()

const features = computed(() => [
  { icon: '📂', title: t('landing.feature1Title'), desc: t('landing.feature1Desc') },
  { icon: '👷', title: t('landing.feature2Title'), desc: t('landing.feature2Desc') },
  { icon: '⏱', title: t('landing.feature3Title'), desc: t('landing.feature3Desc') },
  { icon: '📊', title: t('landing.feature4Title'), desc: t('landing.feature4Desc') },
  { icon: '↓', title: t('landing.feature5Title'), desc: t('landing.feature5Desc') },
  { icon: '🔐', title: t('landing.feature6Title'), desc: t('landing.feature6Desc') },
])

const previewRows = [
  { worker: 'Іванов І.І.', rank: 4, time: '12.5 хв', color: '#6B9AFF' },
  { worker: 'Петренко В.С.', rank: 3, time: '8.2 хв', color: '#54D6B1' },
  { worker: 'Коваль О.М.', rank: 5, time: '15.0 хв', color: '#FF6B6B' },
  { worker: 'Сидоренко П.І.', rank: 3, time: '9.7 хв', color: '#F7D154' },
  { worker: 'Бойко А.В.', rank: 4, time: '11.3 хв', color: '#B36BFF' },
]

function goToApp() {
  if (authStore.isLoggedIn) {
    router.push('/operations')
  } else {
    router.push('/login')
  }
}
</script>

<template>
  <div class="landing">
    <!-- Nav -->
    <nav class="landing-nav">
      <div class="nav-inner">
        <img src="../assets/icons/logo_dark.png" alt="ChronoLogic" class="nav-logo" />
        <div class="nav-actions">
          <button class="lang-toggle" @click="toggleLocale" :title="isEN ? 'Українська' : 'English'">
            {{ isEN ? 'UA' : 'EN' }}
          </button>
          <template v-if="authStore.isLoggedIn">
            <span class="nav-greeting">{{ authStore.username }}</span>
            <button @click="router.push('/operations')" class="btn-primary">{{ t('nav.openApp') }}</button>
          </template>
          <template v-else>
            <button @click="router.push('/login')" class="btn-ghost">{{ t('nav.login') }}</button>
            <button @click="router.push('/register')" class="btn-primary">{{ t('nav.register') }}</button>
          </template>
        </div>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg">
        <div class="hero-orb hero-orb--1"></div>
        <div class="hero-orb hero-orb--2"></div>
        <div class="hero-orb hero-orb--3"></div>
        <div class="hero-grid"></div>
      </div>
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-dot"></span>
          {{ t('landing.badge') }}
        </div>
        <h1 class="hero-title">
          {{ t('landing.title1') }}<br />
          <span class="hero-title-accent">{{ t('landing.title2') }}</span>
        </h1>
        <p class="hero-desc">
          {{ t('landing.desc') }}
        </p>
        <div class="hero-cta">
          <button @click="goToApp" class="btn-hero">
            <span>{{ authStore.isLoggedIn ? t('nav.openApp') : t('nav.start') }}</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
          <div class="hero-stats">
            <div class="hero-stat">
              <span class="hero-stat__n">{{ t('landing.csv') }}</span>
              <span class="hero-stat__l">{{ t('landing.csvLabel') }}</span>
            </div>
            <div class="hero-stat-sep"></div>
            <div class="hero-stat">
              <span class="hero-stat__n">{{ t('landing.files') }}</span>
              <span class="hero-stat__l">{{ t('landing.filesLabel') }}</span>
            </div>
            <div class="hero-stat-sep"></div>
            <div class="hero-stat">
              <span class="hero-stat__n">{{ t('landing.ranks') }}</span>
              <span class="hero-stat__l">{{ t('landing.ranksLabel') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Preview card -->
      <div class="hero-preview">
        <div class="preview-card">
          <div class="preview-header">
            <div class="preview-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="preview-title">operations.csv</span>
          </div>
          <div class="preview-rows">
            <div class="preview-row" v-for="(item, i) in previewRows" :key="i" :style="{ '--row-color': item.color }">
              <span class="preview-color-dot"></span>
              <span class="preview-worker">{{ item.worker }}</span>
              <span class="preview-rank">{{ t('landing.rankFormat', { n: item.rank }) }}</span>
              <span class="preview-time">{{ item.time }}</span>
            </div>
          </div>
          <div class="preview-footer">
            <span class="preview-total">{{ t('landing.previewTotal', { total: '56.7', n: 5 }) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="features">
      <div class="features-inner">
        <h2 class="section-title">{{ t('landing.sectionTitle') }}</h2>
        <p class="section-desc">{{ t('landing.sectionDesc') }}</p>
        <div class="features-grid">
          <div class="feature-card" v-for="(f, i) in features" :key="i">
            <div class="feature-icon">{{ f.icon }}</div>
            <h3 class="feature-title">{{ f.title }}</h3>
            <p class="feature-desc">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Bottom -->
    <section class="cta-section">
      <div class="cta-inner">
        <img src="../assets/icons/logo_dark.png" alt="ChronoLogic" class="cta-logo" />
        <h2 class="cta-title">{{ t('landing.ctaTitle') }}</h2>
        <p class="cta-desc">{{ t('landing.ctaDesc') }}</p>
        <button @click="goToApp" class="btn-hero">
          <span>{{ authStore.isLoggedIn ? t('nav.openApp') : t('nav.startFree') }}</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
      </div>
    </section>

    <!-- Footer -->
    <footer class="landing-footer">
      <div class="footer-inner">
        <img src="../assets/icons/logo_dark.png" alt="ChronoLogic" class="footer-logo" />
        <span class="footer-copy">{{ t('landing.footer') }}</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

.landing {
  font-family: 'Outfit', sans-serif;
  background: #0a0a14;
  color: #e8e8f0;
  min-height: 100vh;
  overflow-x: hidden;
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

.landing-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  background: rgba(10, 10, 20, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 14px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nav-logo { height: 38px; }
.nav-actions { display: flex; align-items: center; gap: 12px; }
.nav-greeting { font-size: 14px; color: #9090b0; }

.btn-ghost {
  padding: 9px 20px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
  background: transparent; color: #c0c0d8;
  font-size: 14px; font-weight: 500; cursor: pointer;
  font-family: 'Outfit', sans-serif;
  transition: all 0.2s;
}
.btn-ghost:hover { background: rgba(255,255,255,0.08); color: #fff; }

.btn-primary {
  padding: 9px 20px; border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #5047e5, #8b3ab3);
  color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
  font-family: 'Outfit', sans-serif;
  transition: all 0.2s;
  box-shadow: 0 0 20px rgba(80,71,229,0.35);
}
.btn-primary:hover { opacity: 0.88; transform: translateY(-1px); }

.btn-hero {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 15px 32px; border-radius: 14px; border: none;
  background: linear-gradient(135deg, #5047e5, #8b3ab3);
  color: #fff; font-size: 16px; font-weight: 700; cursor: pointer;
  font-family: 'Outfit', sans-serif;
  transition: all 0.25s;
  box-shadow: 0 0 40px rgba(80,71,229,0.45), 0 4px 20px rgba(0,0,0,0.3);
}
.btn-hero:hover { transform: translateY(-2px); box-shadow: 0 0 60px rgba(80,71,229,0.55), 0 8px 30px rgba(0,0,0,0.3); }

.hero {
  min-height: 100vh;
  display: flex;
  align-items: center;
  gap: 60px;
  padding: 120px 80px 80px;
  max-width: 1280px;
  margin: 0 auto;
  position: relative;
}
.hero-bg {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none; z-index: 0;
  overflow: hidden;
}
.hero-orb {
  position: absolute; border-radius: 50%;
  filter: blur(80px); opacity: 0.18;
}
.hero-orb--1 { width: 600px; height: 600px; background: #5047e5; top: -200px; left: -100px; }
.hero-orb--2 { width: 500px; height: 500px; background: #8b3ab3; top: 100px; right: -150px; }
.hero-orb--3 { width: 400px; height: 400px; background: #3b82f6; bottom: -100px; left: 30%; }
.hero-grid {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}

.hero-content { flex: 1; min-width: 0; position: relative; z-index: 1; }

.hero-badge {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 7px 16px; border-radius: 20px;
  background: rgba(80,71,229,0.15); border: 1px solid rgba(80,71,229,0.35);
  font-size: 13px; color: #a0a8ff; font-weight: 500;
  margin-bottom: 28px;
}
.badge-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #5047e5;
  box-shadow: 0 0 8px rgba(80,71,229,0.8);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.3); }
}

.hero-title {
  font-size: clamp(36px, 4.5vw, 58px);
  font-weight: 800; line-height: 1.15;
  margin: 0 0 20px; color: #f0f0f8;
  letter-spacing: -0.02em;
}
.hero-title-accent {
  background: linear-gradient(135deg, #6b8cff, #c47dff);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-desc {
  font-size: 17px; line-height: 1.7; color: #8888aa;
  max-width: 520px; margin-bottom: 36px;
}

.hero-cta { display: flex; align-items: center; gap: 32px; flex-wrap: wrap; }
.hero-stats { display: flex; align-items: center; gap: 16px; }
.hero-stat { display: flex; flex-direction: column; align-items: center; }
.hero-stat__n { font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 600; color: #c0c8ff; }
.hero-stat__l { font-size: 11px; color: #666688; }
.hero-stat-sep { width: 1px; height: 32px; background: rgba(255,255,255,0.1); }

.hero-preview {
  flex: 0 0 400px;
  position: relative; z-index: 1;
}
.preview-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  overflow: hidden;
  backdrop-filter: blur(8px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05);
}
.preview-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.03);
}
.preview-dots { display: flex; gap: 6px; }
.preview-dots span {
  width: 10px; height: 10px; border-radius: 50%;
  background: rgba(255,255,255,0.15);
}
.preview-dots span:nth-child(1) { background: #ff5f57; }
.preview-dots span:nth-child(2) { background: #ffbd2e; }
.preview-dots span:nth-child(3) { background: #28c840; }
.preview-title { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #666688; margin-left: 6px; }

.preview-rows { padding: 10px 0; }
.preview-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 18px; font-size: 13px;
  transition: background 0.2s;
}
.preview-row:hover { background: rgba(255,255,255,0.04); }
.preview-color-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--row-color);
  flex-shrink: 0;
  box-shadow: 0 0 8px var(--row-color);
}
.preview-worker { flex: 1; font-weight: 500; color: #d0d0e8; font-size: 13px; }
.preview-rank { font-size: 11px; color: #555577; }
.preview-time { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #8888cc; }
.preview-footer {
  padding: 12px 18px;
  border-top: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.02);
}
.preview-total { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #7070a0; }

.features {
  padding: 80px 32px;
  background: rgba(255,255,255,0.02);
  border-top: 1px solid rgba(255,255,255,0.06);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.features-inner { max-width: 1100px; margin: 0 auto; }
.section-title { font-size: 36px; font-weight: 800; text-align: center; margin: 0 0 10px; color: #f0f0f8; }
.section-desc { text-align: center; color: #666688; font-size: 16px; margin-bottom: 48px; }

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 20px;
}
.feature-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px; padding: 28px;
  transition: all 0.25s;
}
.feature-card:hover {
  background: rgba(255,255,255,0.07);
  border-color: rgba(80,71,229,0.3);
  transform: translateY(-3px);
  box-shadow: 0 8px 30px rgba(80,71,229,0.15);
}
.feature-icon { font-size: 32px; margin-bottom: 14px; }
.feature-title { font-size: 17px; font-weight: 700; color: #e0e0f0; margin: 0 0 8px; }
.feature-desc { font-size: 14px; line-height: 1.6; color: #7070a0; margin: 0; }

.cta-section { padding: 100px 32px; }
.cta-inner { max-width: 600px; margin: 0 auto; text-align: center; }
.cta-logo { height: 50px; margin-bottom: 28px; }
.cta-title { font-size: 38px; font-weight: 800; color: #f0f0f8; margin: 0 0 14px; }
.cta-desc { font-size: 16px; color: #7070a0; margin-bottom: 36px; line-height: 1.6; }

.landing-footer {
  padding: 24px 32px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.footer-inner {
  max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
}
.footer-logo { height: 30px; opacity: 0.55; }
.footer-copy { font-size: 13px; color: #444466; }

@media (max-width: 900px) {
  .hero { flex-direction: column; padding: 100px 24px 60px; gap: 40px; }
  .hero-preview { flex: none; width: 100%; max-width: 400px; }
}
@media (max-width: 640px) {
  .nav-inner { padding: 12px 20px; }
  .hero { padding: 90px 20px 50px; }
  .hero-title { font-size: 32px; }
  .features { padding: 60px 20px; }
  .cta-section { padding: 60px 20px; }
  .hero-cta { flex-direction: column; align-items: flex-start; }
  .nav-actions .btn-ghost { display: none; }
  .footer-inner { flex-direction: column; gap: 10px; text-align: center; }
}
</style>
