/**
 * Кэш справочника в IndexedDB (объём может превышать лимит localStorage).
 * Ключ валидности — reference_version (SHA-256) с сервера.
 */

const DB_NAME = 'capitalview-reference'
const DB_VERSION = 1
const STORE = 'kv'
const KEY = 'bundle'

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onerror = () => reject(req.error)
    req.onsuccess = () => resolve(req.result)
    req.onupgradeneeded = (ev) => {
      const db = ev.target.result
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE)
      }
    }
  })
}

/**
 * @returns {Promise<{ version: string, reference: object } | null>}
 */
export async function getCachedReferenceBundle() {
  if (typeof indexedDB === 'undefined') return null
  try {
    const db = await openDb()
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly')
      const r = tx.objectStore(STORE).get(KEY)
      r.onsuccess = () => resolve(r.result ?? null)
      r.onerror = () => reject(r.error)
    })
  } catch {
    return null
  }
}

/**
 * @param {{ version: string, reference: object }} bundle
 */
export async function setCachedReferenceBundle(bundle) {
  if (typeof indexedDB === 'undefined' || !bundle?.version || !bundle?.reference) return
  try {
    const db = await openDb()
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite')
      tx.objectStore(STORE).put(bundle, KEY)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // квота / приватный режим — игнорируем
  }
}
