/** One accent color per storage paradigm, bound to the CSS custom
 * properties in globals.css - keeps the color choice in exactly one
 * place instead of scattered class-name literals through every phase's
 * components. Postgres/Mongo's real brand colors informed the first two. */

export type PhaseSlug = "postgres" | "nosql" | "warehouse" | "lake" | "lakehouse";

interface PhaseTheme {
  label: string;
  text: string;
  bg: string;
  border: string;
  bgSolid: string;
}

export const PHASE_THEME: Record<PhaseSlug, PhaseTheme> = {
  postgres: {
    label: "Relational",
    text: "text-phase-postgres",
    bg: "bg-phase-postgres/10",
    border: "border-phase-postgres/30",
    bgSolid: "bg-phase-postgres",
  },
  nosql: {
    label: "Document",
    text: "text-phase-nosql",
    bg: "bg-phase-nosql/10",
    border: "border-phase-nosql/30",
    bgSolid: "bg-phase-nosql",
  },
  warehouse: {
    label: "Warehouse",
    text: "text-phase-warehouse",
    bg: "bg-phase-warehouse/10",
    border: "border-phase-warehouse/30",
    bgSolid: "bg-phase-warehouse",
  },
  lake: {
    label: "Lake",
    text: "text-phase-lake",
    bg: "bg-phase-lake/10",
    border: "border-phase-lake/30",
    bgSolid: "bg-phase-lake",
  },
  lakehouse: {
    label: "Lakehouse",
    text: "text-phase-lakehouse",
    bg: "bg-phase-lakehouse/10",
    border: "border-phase-lakehouse/30",
    bgSolid: "bg-phase-lakehouse",
  },
};
