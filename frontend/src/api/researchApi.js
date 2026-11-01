const API_BASE_URL = 'http://127.0.0.1:8000'

async function fetchWithTimeout(
  url,
  options = {},
  timeout = 5000
) {
  const controller = new AbortController()

  const timeoutId = setTimeout(
    () => controller.abort(),
    timeout
  )

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(
        'Research API is not responding on http://127.0.0.1:8000',
        { cause: error }
      )
    }

    throw new Error(
      'Cannot connect to Research API on http://127.0.0.1:8000',
      { cause: error }
    )
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function getFeatures() {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/research/features`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail ||
      'Failed to load research indicators'
    )
  }

  return data
}

export async function getResearchUniverse() {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/research/universe`
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data.detail ||
      'Failed to load research universe'
    )
  }

  return data
}