import type { OptimizationChange } from "@/types/optimize";

const STOP_WORDS = new Set([
  "a",
  "an",
  "the",
  "and",
  "or",
  "to",
  "of",
  "in",
  "for",
  "with",
  "on",
  "at",
  "by",
  "from",
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9+#.\-\s]/g, " ")
    .split(/\s+/)
    .filter((token) => token.length > 2 && !STOP_WORDS.has(token));
}

export function detectAddedKeywords(before: string, after: string): string[] {
  const beforeTokens = new Set(tokenize(before));
  const added: string[] = [];
  for (const token of tokenize(after)) {
    if (!beforeTokens.has(token) && !added.includes(token)) {
      added.push(token);
    }
  }
  return added.slice(0, 8);
}

export function isSkillsReorderChange(change: OptimizationChange): boolean {
  return change.section === "skills" || change.field_path === "skills";
}

export function parseSkillList(value: string): string[] {
  if (!value.trim()) return [];
  if (value.trim().startsWith("[")) {
    try {
      const parsed = JSON.parse(value) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map(String);
      }
    } catch {
      // fall through
    }
  }
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export function buildSkillReorderMeta(before: string, after: string) {
  const beforeSkills = parseSkillList(before);
  const afterSkills = parseSkillList(after);
  return afterSkills.map((skill, index) => {
    const previousIndex = beforeSkills.findIndex(
      (item) => item.toLowerCase() === skill.toLowerCase(),
    );
    return {
      skill,
      currentIndex: index + 1,
      previousIndex: previousIndex >= 0 ? previousIndex + 1 : null,
      moved: previousIndex >= 0 && previousIndex !== index,
    };
  });
}

export function getChangesForSection(
  changes: OptimizationChange[],
  sectionKey: string,
): OptimizationChange[] {
  return changes.filter(
    (change) =>
      change.section === sectionKey ||
      change.field_path === sectionKey ||
      change.field_path?.startsWith(`${sectionKey}[`),
  );
}

export function sectionHasChanges(
  changes: OptimizationChange[],
  sectionKey: string,
): boolean {
  return getChangesForSection(changes, sectionKey).length > 0;
}

export function renderKeywordHighlights(text: string, keywords: string[]) {
  if (!keywords.length) return text;
  const pattern = new RegExp(
    `(${keywords.map((keyword) => keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`,
    "gi",
  );
  const parts = text.split(pattern);
  return parts.map((part, index) => {
    const isKeyword = keywords.some(
      (keyword) => keyword.toLowerCase() === part.toLowerCase(),
    );
    if (!isKeyword) return part;
    return (
      <mark
        key={`${part}-${index}`}
        className="rounded bg-amber-100 px-1 text-amber-950 dark:bg-amber-900/40 dark:text-amber-100"
      >
        {part}
      </mark>
    );
  });
}
