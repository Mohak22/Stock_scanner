const API_BASE_URL = 'http://127.0.0.1:8000'

export async function getFeatures() {
  const response = await fetch(`${API_BASE_URL}/research/features`)

  if (!response.ok) {
    throw new Error('Failed to load research features')
  }

  return response.json()
}

export async function getResearchUniverse() {
  const response = await fetch(
    `${API_BASE_URL}/research/universe`
  )

  if (!response.ok) {
    throw new Error('Failed to load research universe')
  }

  return response.json()
}