/** A hand-drawn illustrated scene (not a stock photo or line icon) - messy,
 * scattered shapes flowing through a funnel into clean, aligned rows. Zero
 * licensing risk since it's authored here, and it illustrates the actual
 * product (raw mess -> clean data) rather than decorating the page with
 * generic art. Colors pulled from the five phase accents so it reads as
 * "this platform," not a stock illustration pack. */
export function PipelineIllustration() {
  return (
    <svg viewBox="0 0 800 240" fill="none" className="h-auto w-full" role="img" aria-label="Messy data flowing through a pipeline into clean, organized rows">
      <g opacity="0.9">
        <rect x="40" y="40" width="22" height="22" rx="5" fill="oklch(0.5 0.15 255)" transform="rotate(-8 51 51)" />
        <circle cx="100" cy="70" r="12" fill="oklch(0.58 0.14 150)" />
        <rect x="50" y="110" width="26" height="18" rx="4" fill="oklch(0.65 0.19 40)" transform="rotate(6 63 119)" />
        <circle cx="130" cy="150" r="10" fill="oklch(0.62 0.11 220)" />
        <rect x="90" y="170" width="20" height="20" rx="5" fill="oklch(0.53 0.18 300)" transform="rotate(12 100 180)" />
        <circle cx="40" cy="160" r="8" fill="oklch(0.5 0.15 255)" />
        <rect x="140" y="50" width="18" height="18" rx="4" fill="oklch(0.58 0.14 150)" transform="rotate(-15 149 59)" />
      </g>

      <path
        d="M190 30 L420 100 L420 140 L190 210 Z"
        fill="oklch(0.78 0.15 85 / 0.35)"
        stroke="oklch(0.78 0.15 85)"
        strokeWidth="2"
      />

      <g>
        {[0, 1, 2, 3].map((row) => (
          <g key={row}>
            {[0, 1, 2, 3, 4].map((col) => (
              <rect
                key={col}
                x={480 + col * 56}
                y={70 + row * 32}
                width="44"
                height="20"
                rx="5"
                fill={row === 2 && col === 2 ? "oklch(0.55 0.15 150 / 0.5)" : "white"}
                stroke="oklch(0.9 0.025 65)"
                strokeWidth="1.5"
              />
            ))}
          </g>
        ))}
      </g>
    </svg>
  );
}
