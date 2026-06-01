import assert from "node:assert/strict";
import { test } from "node:test";

import { matchesKeywords, parseKeywords } from "../src/keywords.js";

test("parseKeywords strips parentheses and trims (the original bug)", () => {
  assert.deepEqual(parseKeywords("*(đón)*(trả)*(giá)*"), ["đón", "trả", "giá"]);
});

test("parseKeywords supports comma separator", () => {
  assert.deepEqual(parseKeywords("đón, trả, giá"), ["đón", "trả", "giá"]);
});

test("matchesKeywords requires every keyword (case-insensitive)", () => {
  assert.equal(matchesKeywords("Cần đón và trả khách, báo giá", "đón*trả*giá"), true);
  assert.equal(matchesKeywords("CẦN ĐÓN TRẢ GIÁ", "đón*trả*giá"), true);
  assert.equal(matchesKeywords("chỉ cần đón thôi", "đón*trả*giá"), false);
});

test("matchesKeywords handles empty input", () => {
  assert.equal(matchesKeywords("", "đón*trả*giá"), false);
  assert.equal(matchesKeywords("đón trả giá", ""), false);
  assert.equal(matchesKeywords(null, "đón"), false);
});
