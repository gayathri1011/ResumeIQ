import { describe, expect, it } from "vitest";

const MAX_UPLOAD_SIZE_MB = 10;
const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".gif"];

function validateFile(file: {
  name: string;
  type: string;
  size: number;
}): string | null {
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
  if (!ACCEPTED_EXTENSIONS.includes(extension)) {
    return "Only PDF, DOCX, and image files (PNG, JPG, WEBP) are supported.";
  }
  const maxBytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
  if (file.size > maxBytes) {
    return `File exceeds the maximum size of ${MAX_UPLOAD_SIZE_MB} MB.`;
  }
  if (file.size === 0) {
    return "The selected file is empty.";
  }
  return null;
}

describe("resume upload validation", () => {
  it("rejects unsupported extensions", () => {
    expect(
      validateFile({ name: "resume.txt", type: "text/plain", size: 100 }),
    ).toBe(
      "Only PDF, DOCX, and image files (PNG, JPG, WEBP) are supported.",
    );
  });

  it("rejects empty files", () => {
    expect(
      validateFile({ name: "resume.pdf", type: "application/pdf", size: 0 }),
    ).toBe("The selected file is empty.");
  });

  it("accepts valid PDF files", () => {
    expect(
      validateFile({ name: "resume.pdf", type: "application/pdf", size: 1024 }),
    ).toBeNull();
  });

  it("accepts image resumes", () => {
    expect(
      validateFile({ name: "resume.png", type: "image/png", size: 2048 }),
    ).toBeNull();
    expect(
      validateFile({ name: "resume.jpg", type: "image/jpeg", size: 2048 }),
    ).toBeNull();
    expect(
      validateFile({ name: "resume.webp", type: "image/webp", size: 2048 }),
    ).toBeNull();
  });
});
