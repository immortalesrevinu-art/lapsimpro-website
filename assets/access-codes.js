// Allowed access codes live here only as lowercase SHA-256 hex digests.
// Add another digest to the list to accept another code.
export const ALLOWED_ACCESS_CODE_HASHES = [
  "f9c67c5045d2151dcb760b4871fbd9c1b292294d72380a1d0ed35e3716ce1f2a",
];

export function normalizeAccessCode(value) {
  return String(value ?? "").trim().toLowerCase();
}

export async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function digestMatchesAllowed(digestHex, allowed = ALLOWED_ACCESS_CODE_HASHES) {
  const digest = String(digestHex ?? "").trim().toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(digest)) return false;
  return allowed.some((hash) => String(hash).trim().toLowerCase() === digest);
}

export async function accessCodeMatches(raw, allowed = ALLOWED_ACCESS_CODE_HASHES) {
  const normalized = normalizeAccessCode(raw);
  if (!normalized) return false;
  const digest = await sha256Hex(normalized);
  return digestMatchesAllowed(digest, allowed);
}
