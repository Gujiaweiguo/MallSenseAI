import { createI18n } from 'vue-i18n';

import en from './locales/en.json';
import zhCN from './locales/zh-CN.json';

export const SUPPORT_LOCALES = ['zh-CN', 'en'] as const;
export type AppLocale = (typeof SUPPORT_LOCALES)[number];

export const DEFAULT_LOCALE: AppLocale = 'zh-CN';
const STORAGE_KEY = 'mallsenseai.locale';

function getInitialLocale(): AppLocale {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && (SUPPORT_LOCALES as readonly string[]).includes(stored)) {
    return stored as AppLocale;
  }
  const browserLang = navigator.language;
  if (browserLang.startsWith('zh')) return 'zh-CN';
  if (browserLang.startsWith('en')) return 'en';
  return DEFAULT_LOCALE;
}

const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages: {
    'zh-CN': zhCN,
    en,
  },
});

export default i18n;

export function setLocale(locale: AppLocale): void {
  i18n.global.locale.value = locale;
  localStorage.setItem(STORAGE_KEY, locale);
  document.documentElement.setAttribute('lang', locale);
}

export const t = i18n.global.t;
