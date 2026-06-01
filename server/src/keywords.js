/**
 * Parse a keyword string into a clean list of keywords.
 *
 * Accepts both "*" and "," as separators and strips surrounding parentheses /
 * whitespace, so values like "*(đón)*(trả)*(giá)*" and "đón, trả, giá" both
 * resolve to ["đón", "trả", "giá"].
 *
 * @param {string} keywordString
 * @returns {string[]}
 */
export const parseKeywords = (keywordString) => {
  if (!keywordString) return [];
  return keywordString
    .split(/[*,]/)
    .map((kw) => kw.replace(/[()]/g, "").trim())
    .filter((kw) => kw !== "");
};

/**
 * Returns true when every keyword is present (case-insensitive) in the text.
 *
 * @param {string} text
 * @param {string} keywordString
 * @returns {boolean}
 */
export const matchesKeywords = (text, keywordString) => {
  const keywords = parseKeywords(keywordString);
  if (keywords.length === 0) return false;
  if (typeof text !== "string" || text.length === 0) return false;
  const lowerText = text.toLowerCase();
  return keywords.every((kw) => lowerText.includes(kw.toLowerCase()));
};
