const FALLBACK_PATH = "/diary";
const CONTROL_OR_BACKSLASH = /[\u0000-\u001f\u007f\\\\]/;
const LEADING_OR_TRAILING_WHITESPACE = /^\s|\s$/u;
const ENCODED_SEPARATOR = /%(?:2f|5c)/i;
const MALFORMED_PERCENT_ENCODING = /%(?![0-9a-f]{2})/i;

function hasNestedEncodedSeparator(value: string): boolean {
  let candidate = value;
  for (let decodeCount = 0; decodeCount <= 4; decodeCount += 1) {
    if (ENCODED_SEPARATOR.test(candidate)) return true;
    const decodedPercentSigns = candidate.replace(/%25/gi, "%");
    if (decodedPercentSigns === candidate) return false;
    if (decodeCount === 4) return true;
    candidate = decodedPercentSigns;
  }
  return true;
}

/**
 * Returns a route which is guaranteed to remain on the current application origin.
 */
export function normalizePostLoginPath(raw: string | null, origin: string): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return FALLBACK_PATH;

  try {
    const applicationOrigin = new URL(origin).origin;
    if (
      CONTROL_OR_BACKSLASH.test(raw) ||
      LEADING_OR_TRAILING_WHITESPACE.test(raw) ||
      MALFORMED_PERCENT_ENCODING.test(raw) ||
      hasNestedEncodedSeparator(raw)
    ) return FALLBACK_PATH;

    const target = new URL(raw, applicationOrigin);
    if (
      target.origin !== applicationOrigin ||
      target.username ||
      target.password ||
      target.pathname.startsWith("//")
    ) return FALLBACK_PATH;

    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return FALLBACK_PATH;
  }
}
