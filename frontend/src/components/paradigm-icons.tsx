import type { SVGProps } from "react";
import type { PhaseSlug } from "@/lib/phase-theme";

/** Small, hand-built schematic illustrations - one per paradigm, not stock
 * photography (licensing risk, and less honest about what the product
 * actually is). Each one is a simplified preview of that paradigm's real
 * data-visualizer concept from CURRICULUM_STRUCTURE.md - a schema grid, a
 * document tree, a star schema, a partitioned file layout, a commit
 * timeline - so the homepage imagery previews the real product instead of
 * decorating it. `currentColor` throughout so phase-theme text color
 * classes control the stroke/fill from the call site. */

function PostgresIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 64 64" fill="none" {...props}>
      <rect x="6" y="10" width="52" height="44" rx="4" stroke="currentColor" strokeWidth="2" />
      <line x1="6" y1="24" x2="58" y2="24" stroke="currentColor" strokeWidth="2" />
      <line x1="24" y1="10" x2="24" y2="54" stroke="currentColor" strokeWidth="2" />
      <line x1="42" y1="10" x2="42" y2="54" stroke="currentColor" strokeWidth="2" />
      <line x1="6" y1="38" x2="58" y2="38" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <rect x="10" y="14" width="10" height="6" rx="1.5" fill="currentColor" opacity="0.25" />
    </svg>
  );
}

function NosqlIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 64 64" fill="none" {...props}>
      <path d="M18 8 C10 8 10 16 10 20 C10 24 6 24 6 28 C6 32 10 32 10 36 C10 40 10 48 18 48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M46 8 C54 8 54 16 54 20 C54 24 58 24 58 28 C58 32 54 32 54 36 C54 40 54 48 46 48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="32" cy="18" r="3" fill="currentColor" opacity="0.6" />
      <circle cx="24" cy="30" r="3" fill="currentColor" opacity="0.6" />
      <circle cx="40" cy="30" r="3" fill="currentColor" opacity="0.6" />
      <circle cx="32" cy="42" r="3" fill="currentColor" opacity="0.6" />
      <line x1="32" y1="18" x2="24" y2="30" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
      <line x1="32" y1="18" x2="40" y2="30" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
      <line x1="24" y1="30" x2="32" y2="42" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
    </svg>
  );
}

function WarehouseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 64 64" fill="none" {...props}>
      <circle cx="32" cy="30" r="8" fill="currentColor" opacity="0.3" stroke="currentColor" strokeWidth="2" />
      <circle cx="32" cy="10" r="5" stroke="currentColor" strokeWidth="2" />
      <circle cx="14" cy="22" r="5" stroke="currentColor" strokeWidth="2" />
      <circle cx="14" cy="42" r="5" stroke="currentColor" strokeWidth="2" />
      <circle cx="32" cy="54" r="5" stroke="currentColor" strokeWidth="2" />
      <circle cx="50" cy="42" r="5" stroke="currentColor" strokeWidth="2" />
      <circle cx="50" cy="22" r="5" stroke="currentColor" strokeWidth="2" />
      <line x1="32" y1="22" x2="32" y2="15" stroke="currentColor" strokeWidth="1.5" />
      <line x1="25" y1="26" x2="18" y2="23" stroke="currentColor" strokeWidth="1.5" />
      <line x1="25" y1="34" x2="18" y2="39" stroke="currentColor" strokeWidth="1.5" />
      <line x1="32" y1="38" x2="32" y2="49" stroke="currentColor" strokeWidth="1.5" />
      <line x1="39" y1="34" x2="46" y2="39" stroke="currentColor" strokeWidth="1.5" />
      <line x1="39" y1="26" x2="46" y2="23" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function LakeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 64 64" fill="none" {...props}>
      <rect x="8" y="8" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
      <rect x="32" y="8" width="24" height="14" rx="2" stroke="currentColor" strokeWidth="2" opacity="0.6" />
      <rect x="8" y="26" width="24" height="14" rx="2" stroke="currentColor" strokeWidth="2" opacity="0.6" />
      <rect x="36" y="26" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
      <rect x="8" y="44" width="16" height="12" rx="2" stroke="currentColor" strokeWidth="2" opacity="0.6" />
      <rect x="28" y="44" width="28" height="12" rx="2" stroke="currentColor" strokeWidth="2" />
      <text x="13" y="18" fontSize="7" fill="currentColor" opacity="0.5">2024</text>
      <text x="41" y="18" fontSize="7" fill="currentColor" opacity="0.5">2025</text>
    </svg>
  );
}

function LakehouseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 64 64" fill="none" {...props}>
      <line x1="8" y1="32" x2="56" y2="32" stroke="currentColor" strokeWidth="2" opacity="0.4" />
      <circle cx="14" cy="32" r="4" fill="currentColor" opacity="0.3" stroke="currentColor" strokeWidth="2" />
      <circle cx="30" cy="32" r="4" fill="currentColor" stroke="currentColor" strokeWidth="2" />
      <circle cx="46" cy="32" r="4" fill="currentColor" opacity="0.3" stroke="currentColor" strokeWidth="2" />
      <path d="M14 32 L14 16" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.5" />
      <path d="M30 32 L30 16" stroke="currentColor" strokeWidth="1.5" />
      <rect x="22" y="8" width="16" height="8" rx="1.5" stroke="currentColor" strokeWidth="2" />
      <path d="M46 32 L46 48" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.5" />
    </svg>
  );
}

export const PARADIGM_ICONS: Record<PhaseSlug, (props: SVGProps<SVGSVGElement>) => React.ReactElement> = {
  postgres: PostgresIcon,
  nosql: NosqlIcon,
  warehouse: WarehouseIcon,
  lake: LakeIcon,
  lakehouse: LakehouseIcon,
};
