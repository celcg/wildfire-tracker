const CLIENT_ID_STORAGE_KEY = "wildfire-client-id:v1";
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

let inMemoryClientId;

export function loadOrCreateClientId({ storage, randomUUID }) {
  try {
    const stored = storage?.getItem(CLIENT_ID_STORAGE_KEY);
    if (UUID_PATTERN.test(stored ?? "")) {
      return stored;
    }
  } catch {
    // Private browsing and hardened browsers can disable localStorage.
  }

  const generated = randomUUID();
  try {
    storage?.setItem(CLIENT_ID_STORAGE_KEY, generated);
  } catch {
    // The in-memory fallback still provides a stable ID for this page load.
  }
  return generated;
}

export function getClientId() {
  if (!inMemoryClientId) {
    inMemoryClientId = loadOrCreateClientId({
      storage: globalThis.localStorage,
      randomUUID: () => globalThis.crypto.randomUUID(),
    });
  }
  return inMemoryClientId;
}
