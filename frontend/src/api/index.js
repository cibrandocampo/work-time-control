const API_BASE = '/api'

class ApiClient {
  constructor() {
    this.accessToken = localStorage.getItem('accessToken')
    this.refreshToken = localStorage.getItem('refreshToken')
  }

  setTokens(access, refresh) {
    this.accessToken = access
    this.refreshToken = refresh
    localStorage.setItem('accessToken', access)
    localStorage.setItem('refreshToken', refresh)
  }

  clearTokens() {
    this.accessToken = null
    this.refreshToken = null
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`
    const headers = {
      ...options.headers
    }

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(url, {
      ...options,
      headers
    })

    // Token expired - try refresh
    if (response.status === 401 && this.refreshToken) {
      const refreshed = await this.refreshAccessToken()
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.accessToken}`
        return fetch(url, { ...options, headers })
      }
    }

    return response
  }

  async refreshAccessToken() {
    try {
      const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: this.refreshToken })
      })

      if (response.ok) {
        const data = await response.json()
        this.accessToken = data.access
        localStorage.setItem('accessToken', data.access)
        return true
      }
    } catch (e) {
      console.error('Token refresh failed:', e)
    }

    this.clearTokens()
    return false
  }

  // Auth
  async login(username, password) {
    const response = await fetch(`${API_BASE}/auth/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })

    if (response.ok) {
      const data = await response.json()
      this.setTokens(data.access, data.refresh)
      return { success: true }
    }

    return { success: false, error: 'Invalid credentials' }
  }

  async getMe() {
    const response = await this.request('/me/')
    if (response.ok) {
      return response.json()
    }
    return null
  }

  async changePassword(currentPassword, newPassword) {
    const response = await this.request('/me/change-password/', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword
      })
    })
    return response.ok
  }

  async updateProfile(data) {
    const response = await this.request('/me/', {
      method: 'PATCH',
      body: JSON.stringify(data)
    })
    if (response.ok) {
      return response.json()
    }
    throw new Error('Failed to update profile')
  }

  // Signings
  async getActiveSigning() {
    const response = await this.request('/signings/active/')
    if (response.ok) {
      const data = await response.json()
      return data.active !== undefined ? data.active : data
    }
    return null
  }

  async createSigning(data) {
    const response = await this.request('/signings/', {
      method: 'POST',
      body: JSON.stringify(data)
    })
    if (response.ok) {
      return response.json()
    }
    throw new Error('Failed to create signing')
  }

  async checkoutSigning(id, endTime = null) {
    const body = endTime ? { end_time: endTime } : {}
    const response = await this.request(`/signings/${id}/checkout/`, {
      method: 'POST',
      body: JSON.stringify(body)
    })
    if (response.ok) {
      return response.json()
    }
    throw new Error('Failed to checkout')
  }

  async getSignings(params = {}) {
    const query = new URLSearchParams(params).toString()
    const response = await this.request(`/signings/?${query}`)
    if (response.ok) {
      return response.json()
    }
    return []
  }

  async updateSigning(id, data) {
    const response = await this.request(`/signings/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    })
    if (response.ok) {
      return response.json()
    }
    throw new Error('Failed to update signing')
  }

  async deleteSigning(id) {
    const response = await this.request(`/signings/${id}/`, {
      method: 'DELETE'
    })
    return response.ok
  }

  // Summaries
  async getDaySummary(date = null) {
    const endpoint = date ? `/summary/day/${date}/` : '/summary/day/'
    const response = await this.request(endpoint)
    if (response.ok) {
      return response.json()
    }
    return null
  }

  async getRangeSummary(startDate, endDate) {
    const response = await this.request(`/summary/range/?start_date=${startDate}&end_date=${endDate}`)
    if (response.ok) return response.json()
    return null
  }

  // Import/Export
  async exportSignings(startDate, endDate) {
    const response = await this.request(
      `/signings/export/?start_date=${startDate}&end_date=${endDate}`
    )
    if (response.ok) {
      return response.blob()
    }
    throw new Error('Export failed')
  }

  async importSignings(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.request('/signings/import/', {
      method: 'POST',
      body: formData
    })

    return response.json()
  }

  // Locations
  async getLocations() {
    const response = await this.request('/locations/')
    if (response.ok) {
      return response.json()
    }
    return []
  }
}

export const api = new ApiClient()
