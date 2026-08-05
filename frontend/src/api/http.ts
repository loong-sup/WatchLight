/** REST API client */

const BASE = '/api'

export async function fetchJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`)
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export const api = {
  getConfig: () => fetchJson<any>('/config'),
  getSessions: () => fetchJson<any>('/sessions'),
  getModels: () => fetchJson<any>('/models'),
  getChannelStatus: () => fetchJson<any>('/channels/status'),
  getStatus: () => fetchJson<any>('/status'),
  getDiagnostics: () => fetchJson<any>('/diagnostics'),
}
