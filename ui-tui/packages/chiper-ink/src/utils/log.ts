export function logError(error: unknown): void {
  if (!process.env.CHIPER_INK_DEBUG_ERRORS) {
    return
  }

  console.error(error)
}
