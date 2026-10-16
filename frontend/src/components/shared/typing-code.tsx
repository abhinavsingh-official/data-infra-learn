"use client";

import { useEffect, useState } from "react";

/** Module 24: the homepage's `QueryDemo` types code out character-by-
 * character in a loop; this is the same typing mechanic extracted as a
 * standalone, one-shot (not looping) piece so a second page can get the
 * same signature motion without cloning QueryDemo's hero-specific
 * before/after state machine. Used on /compare, where five real code
 * snippets already exist as static text - typing them out once on mount
 * is the actual "propagate the animated-demo pattern" ask for Module 24,
 * not a decorative addition. */
const MS_PER_CHAR = 10;

export function TypingCode({ code }: { code: string }) {
  const [typedChars, setTypedChars] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    setTypedChars(0);
    setDone(false);
    const interval = setInterval(() => {
      setTypedChars((count) => {
        if (count >= code.length) {
          clearInterval(interval);
          setDone(true);
          return count;
        }
        return count + 1;
      });
    }, MS_PER_CHAR);
    return () => clearInterval(interval);
  }, [code]);

  return (
    <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs">
      <code>
        {code.slice(0, typedChars)}
        {!done && <span className="animate-pulse">▍</span>}
      </code>
    </pre>
  );
}
