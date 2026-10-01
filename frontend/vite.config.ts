import { fileURLToPath, URL } from 'node:url'
import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import JavaScriptObfuscator from 'javascript-obfuscator'

const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

/** 前端代码混淆：默认开启，排障时用 OBFS_ENABLE=false 关闭 */
const OBFS_ENABLE = (process.env.OBFS_ENABLE ?? 'true').toLowerCase() !== 'false'
/** 第三方库占比高的超大 chunk 不混淆：收益低、构建慢、且易引入兼容问题 */
const OBFS_MAX_KB = 400

/**
 * 混淆业务代码（自定义 Vite 插件，不额外引入插件依赖）。
 *
 * 定位：这只是「提高读代码门槛」，不是「防逆向」——
 * 前端代码在浏览器里终究要被执行，任何混淆都能被还原，真正的保护是 SaaS 自营交付。
 * 因此此处刻意使用保守配置（不开 selfDefending / debugProtection，避免破坏运行与调试）。
 */
function obfuscateAppChunks(): Plugin {
  let count = 0
  let totalBefore = 0
  let totalAfter = 0
  return {
    name: 'obfuscate-app-chunks',
    apply: 'build',
    enforce: 'post',
    renderChunk(code, chunk) {
      if (!OBFS_ENABLE || !chunk.fileName.endsWith('.js')) return null
      const sizeKb = Buffer.byteLength(code) / 1024
      if (sizeKb > OBFS_MAX_KB) return null
      const result = JavaScriptObfuscator.obfuscate(code, {
        compact: true,
        identifierNamesGenerator: 'hexadecimal',
        renameGlobals: false,
        stringArray: true,
        stringArrayThreshold: 0.6,
        stringArrayEncoding: ['base64'],
        rotateStringArray: true,
        controlFlowFlattening: true,
        controlFlowFlatteningThreshold: 0.35,
        deadCodeInjection: false,
        selfDefending: false,
        debugProtection: false,
        disableConsoleOutput: true,
        simplify: true,
        splitStrings: false,
        unicodeEscapeSequence: false,
        target: 'browser',
      })
      const output = result.getObfuscatedCode()
      count += 1
      totalBefore += sizeKb
      totalAfter += Buffer.byteLength(output) / 1024
      return { code: output, map: null }
    },
    closeBundle() {
      if (!OBFS_ENABLE) {
        console.log('[混淆] 已按 OBFS_ENABLE=false 关闭')
        return
      }
      console.log(
        `[混淆] 已混淆 ${count} 个业务 chunk：${totalBefore.toFixed(0)}KB → ${totalAfter.toFixed(0)}KB`
        + `（超过 ${OBFS_MAX_KB}KB 的第三方大包未混淆）`,
      )
    },
  }
}

export default defineConfig({
  plugins: [vue(), obfuscateAppChunks()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/media': { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500,
  },
})