import { API_BASE_URL } from '../env'

export type ApiError = { status: number; message: string }

async function parseError(res: Response): Promise<ApiError> {
  try {
    const data = (await res.json()) as { detail?: string }
    return { status: res.status, message: data.detail ?? res.statusText }
  } catch {
    return { status: res.status, message: res.statusText }
  }
}

export async function apiFetch<T>(
  path: string,
  opts: RequestInit & { token?: string } = {},
): Promise<T> {
  const { token, headers, ...rest } = opts
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers ?? {}),
    },
  })
  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

