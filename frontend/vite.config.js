import { rmSync } from 'node:fs'
import { resolve } from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// MSW 워커는 개발(npm run dev)에서만 쓴다. public/ 에서 복사된 파일을 빌드 결과에서 지운다
function dropMockWorker() {
  let outDir = 'dist'
  return {
    name: 'drop-mock-worker',
    apply: 'build',
    configResolved(c) {
      outDir = resolve(c.root, c.build.outDir)
    },
    closeBundle() {
      rmSync(resolve(outDir, 'mockServiceWorker.js'), { force: true })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), dropMockWorker()],
  server: {
    proxy: { '/api': 'http://localhost:8080' },
    fs: { allow: ['.', '../mock-data'] },
  },
})
