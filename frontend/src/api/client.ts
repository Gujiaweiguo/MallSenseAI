import axios from 'axios';
import type { AxiosError, AxiosInstance } from 'axios';

import { AUTH_TOKEN_STORAGE_KEY, AUTH_USER_STORAGE_KEY } from '@/auth/storage';

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

client.interceptors.request.use((config) => {
  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (token !== null && token.length > 0) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function isUnauthorizedError(error: unknown): error is AxiosError {
  return axios.isAxiosError(error) && error.response?.status === 401;
}

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (isUnauthorizedError(error)) {
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);

      if (window.location.pathname !== '/login') {
        const redirect = `${window.location.pathname}${window.location.search}`;
        window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`);
      }
    }

    return Promise.reject(error);
  },
);

export default client;
