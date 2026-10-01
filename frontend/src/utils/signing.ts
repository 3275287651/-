/**
 * 请求签名（防篡改 + 防重放）。
 *
 * 规则与服务端 app/hardening.py 的 sign_request 完全一致：
 *   签名字符串 = METHOD \n PATH \n 时间戳 \n nonce \n sha256(请求体)
 *   签名 = HMAC-SHA256(签名字符串, key=登录令牌)
 *
 * 说明：
 * - 只要登录令牌存在就自动签名（服务端未开启校验时会忽略这些头，避免前后端开关不同步）；
 * - 文件上传（FormData）无法在浏览器端稳定复算字节，约定用空体摘要，并带 X-Body-Mode: skip；
 * - Web Crypto 只在安全上下文（HTTPS 或 localhost）可用，HTTP 部署会无法签名，
 *   生产环境必须上 HTTPS —— 这既是安全要求，也是该机制的前置条件。
 */
const WRITE_METHODS = ['post', 'put', 'patch', 'delete']
const SKIP_PREFIXES = ['/api/auth/', '/api/admin/auth/', '/api/admin/system/']

let warned = false

function canSign(): boolean {
  return typeof crypto !== 'undefined' && !!crypto.subtle
}

function warnOnce() {
  if (warned) return
  warned = true
  console.warn(
    '[签名] 当前不是安全上下文（需 HTTPS 或 localhost），浏览器 Web Crypto 不可用，'
    + '无法为请求签名；若服务端已开启 SIGN_MODE，写操作将被拒绝。',
  )
}

export function signRequired(method: string, url: string): boolean {
  const path = (url || '').split('?')[0]
  if (!path.startsWith('/api/')) return false
  if (SKIP_PREFIXES.some((p) => path.startsWith(p))) return false
  return WRITE_METHODS.includes(method.toLowerCase())
}

async function hmacSha256Hex(key: string, message: string): Promise<string> {
  const enc = new TextEncoder()
  const cryptoKey = await crypto.subtle.importKey(
    'raw', enc.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  )
  const signature = await crypto.subtle.sign('HMAC', cryptoKey, enc.encode(message))
  return toHex(signature)
}

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return toHex(digest)
}

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

function nonce(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('')
}

export interface SignedHeaders {
  'X-TS': string
  'X-Nonce': string
  'X-Sign': string
  'X-Body-Mode'?: 'skip'
}

/**
 * 计算签名头。
 * @param token 登录令牌（HMAC 密钥）
 * @param bodyText 已序列化的请求体；FormData 上传时传空且 skipBody=true
 */
export async function buildSignedHeaders(
  token: string, method: string, url: string, bodyText: string, skipBody: boolean,
): Promise<SignedHeaders | null> {
  if (!canSign()) {
    warnOnce()
    return null
  }
  const path = (url || '').split('?')[0]
  const ts = String(Math.floor(Date.now() / 1000))
  const nc = nonce()
  const digest = skipBody ? await sha256Hex('') : await sha256Hex(bodyText)
  const message = `${method.toUpperCase()}\n${path}\n${ts}\n${nc}\n${digest}`
  const sign = await hmacSha256Hex(token, message)
  const headers: SignedHeaders = { 'X-TS': ts, 'X-Nonce': nc, 'X-Sign': sign }
  if (skipBody) headers['X-Body-Mode'] = 'skip'
  return headers
}