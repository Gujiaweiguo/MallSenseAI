import ElementPlus from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import 'element-plus/dist/index.css';

import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import i18n from './i18n';
import router from './router';
import './styles.css';

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(i18n);
app.use(ElementPlus, { locale: zhCn });

app.mount('#app');
