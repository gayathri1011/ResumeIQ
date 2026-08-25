"use client";

import { useCallback, useRef } from "react";

/** Prevents overlapping async actions from rapid double-clicks. */
export function useActionLock() {
  const lockedRef = useRef(false);

  const runLocked = useCallback(async <T>(action: () => Promise<T>): Promise<T | undefined> => {
    if (lockedRef.current) {
      return undefined;
    }
    lockedRef.current = true;
    try {
      return await action();
    } finally {
      lockedRef.current = false;
    }
  }, []);

  return runLocked;
}
