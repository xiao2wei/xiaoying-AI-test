let csrf = ''
export function configureApi(value) { csrf = value }
export class ApiError extends Error {
  constructor(message, code, status) {
    super(message)
    this.code = code
    this.status = status
  }
}
export async function api(path, { method = 'GET', body, timeout = 12000 } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(path, {
      method, signal: controller.signal, credentials: 'same-origin',
      headers: method === 'GET' ? {} : { 'Content-Type': 'application/json', 'X-Policy-CSRF': csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const data = await response.json()
    if (!response.ok) throw new ApiError(data.error?.message || '本地服务返回错误。', data.error?.code, response.status)
    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('无法连接本地服务，请检查服务是否仍在运行。不会自动重新发起模型请求。', 'NETWORK_ERROR', 0)
  } finally {
    clearTimeout(timer)
  }
}
