const BASE = 'https://eco-lens-production.up.railway.app'

async function request(method, path, body, token) {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || data.message || `Server error ${res.status}`)
  return data
}

export const api = {
  login:         (email, password)    => request('POST', '/api/admin/login',                    { email, password }),
  overview:      (tok)                => request('GET',  '/api/admin/overview',                  null, tok),
  kiosks:        (tok)                => request('GET',  '/api/admin/kiosks',                    null, tok),
  kiosk:         (tok, id)            => request('GET',  `/api/admin/kiosks/${id}`,              null, tok),
  registerKiosk: (tok, data)          => request('POST', '/api/admin/kiosks',                    data, tok),
  updateKiosk:   (tok, id, data)      => request('PATCH',`/api/admin/kiosks/${id}`,              data, tok),
  resetCapacity: (tok, id)            => request('POST', `/api/admin/kiosks/${id}/reset-capacity`, {}, tok),
  redemptions:   (tok)                => request('GET',  '/api/admin/redemptions',               null, tok),
}
