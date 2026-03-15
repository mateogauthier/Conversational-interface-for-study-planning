/**
 * Maps backend error detail to a user-facing message.
 * If UI language is Spanish, returns translated message; if English, returns detail as-is.
 * Used when the HTTP request itself falla (status 4xx/5xx).
 */
export function getErrorMessage(detail, t, language) {
  if (!detail) return t('home.errorMessage');
  const isSpanish = language?.startsWith('es');
  if (!isSpanish) return detail;
  const d = String(detail).toLowerCase();
  if (d.includes('does not support tools') || d.includes("doesn't support tools")) return t('home.errors.doesNotSupportTools');
  if (d.includes('agent provider not initialized')) return t('home.errors.agentNotInitialized');
  if (d.includes('temporarily unavailable') || d.includes('not available')) return t('home.errors.agentUnavailable');
  if (d.includes('agent tools are disabled')) return t('home.errors.agentToolsDisabled');
  return t('home.errorMessage');
}

/**
 * Detects when the *answer text itself* is an English error string from the agent
 * and returns a Spanish version if applicable. For normal answers, it just returns
 * the original text.
 */
export function maybeTranslateAgentError(answer, t, language) {
  if (!answer) return answer;
  const isSpanish = language?.startsWith('es');
  if (!isSpanish) return answer;
  const d = String(answer).toLowerCase();

  if (d.includes('does not support tools') || d.includes("doesn't support tools")) {
    return t('home.errors.doesNotSupportTools');
  }

  if (d.includes('agent provider not initialized')) {
    return t('home.errors.agentNotInitialized');
  }

  if (d.includes('temporarily unavailable') || d.includes('not available')) {
    return t('home.errors.agentUnavailable');
  }

  if (d.includes('agent tools are disabled')) {
    return t('home.errors.agentToolsDisabled');
  }

  // For any other text (including model not found, etc.) keep the original,
  // so we don't overwite valid answers with a generic error.
  return answer;
}
