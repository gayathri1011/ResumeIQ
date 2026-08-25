import { describe, expect, it } from "vitest";

import { getUserFriendlyErrorMessage, isRetryableErrorCode } from "@/lib/error-messages";
import { ApiClientError } from "@/lib/api-client";

describe("getUserFriendlyErrorMessage", () => {
  it("maps known API error codes to friendly copy", () => {
    const error = new ApiClientError(
      "raw provider traceback at module.py:42",
      502,
      "ai_provider_error",
    );

    expect(getUserFriendlyErrorMessage(error)).toBe(
      "AI service is temporarily unavailable. Please try again in a moment.",
    );
  });

  it("sanitizes internal-looking messages for unknown codes", () => {
    const error = new ApiClientError(
      "Traceback (most recent call last): secret",
      500,
      "unknown_code",
    );

    expect(getUserFriendlyErrorMessage(error)).toBe(
      "Something went wrong. Please try again.",
    );
  });

  it("falls back for non-API errors", () => {
    expect(getUserFriendlyErrorMessage(new Error("boom"), "Custom fallback")).toBe(
      "boom",
    );
  });
});

describe("isRetryableErrorCode", () => {
  it("flags transient failures as retryable", () => {
    expect(isRetryableErrorCode("ai_provider_error")).toBe(true);
    expect(isRetryableErrorCode("network_error")).toBe(true);
    expect(isRetryableErrorCode("invalid_credentials")).toBe(false);
  });
});
