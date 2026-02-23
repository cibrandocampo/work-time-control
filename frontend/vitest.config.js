import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.{test,spec}.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov', 'json-summary', 'json'],
      include: ['src/**/*.{js,vue}'],
      exclude: [
        'src/main.js',
        'src/test/**',
        'src/**/*.spec.js',
        'src/**/*.test.js'
      ],
      thresholds: {
        global: {
          statements: 80,
          branches: 80,
          functions: 70,
          lines: 80
        }
      }
    }
  }
})
