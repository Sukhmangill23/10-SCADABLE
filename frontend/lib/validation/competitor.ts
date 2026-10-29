const NAME_MAX = 255;
const URL_MAX = 2048;

export type CompetitorFormErrors = {
  name?: string;
  website?: string;
};

/** Normalize a website field to an https URL string, or null if unusable. */
export function normalizeWebsiteInput(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  let candidate = trimmed;
  if (!/^[a-z][a-z0-9+.-]*:/i.test(candidate)) {
    candidate = `https://${candidate}`;
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return null;
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return null;
  }
  if (!parsed.hostname.includes(".")) {
    return null;
  }
  if (parsed.username || parsed.password) {
    return null;
  }

  return parsed.toString();
}

export function validateCompetitorForm(
  name: string,
  website: string,
): CompetitorFormErrors {
  const errors: CompetitorFormErrors = {};
  const trimmedName = name.trim();
  const trimmedWebsite = website.trim();

  if (!trimmedName) {
    errors.name = "Company name is required.";
  } else if (trimmedName.length > NAME_MAX) {
    errors.name = `Company name must be at most ${NAME_MAX} characters.`;
  }

  if (!trimmedWebsite) {
    errors.website = "Website link is required.";
  } else if (trimmedWebsite.length > URL_MAX) {
    errors.website = `Website must be at most ${URL_MAX} characters.`;
  } else if (!normalizeWebsiteInput(trimmedWebsite)) {
    errors.website =
      "Enter a valid http(s) website (e.g. example.com or https://example.com).";
  }

  return errors;
}
