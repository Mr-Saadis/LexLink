// src/theme/theme.ts

// Primary Green Scheme
export const NAVY = "#064E3B";        // Dark Emerald Green (Replaces dark navy for headers/sidebars)
export const NAVY_LIGHT = "#047857";  // Medium Emerald Green (Replaces secondary dark navy)
export const GREEN = "#10B981";       // Vibrant Mint Green (Primary accent/success)
export const GREEN_DARK = "#065F46";  // Deep Forest Green
export const GREEN_LIGHT = "#D1FAE5"; // Soft Sage Green (Card highlights/badges)

// Utility Colors
export const BLUE = "#10B981";        // Mapped to Green for active states
export const RED = "#EF4444";         // Maintained for errors & failed jobs
export const BORDER = "#E2E8F0";      // Subtle light border
export const MUTED = "#64748B";       // Muted text
export const TEXT = "#0F172A";        // Dark text color
export const BG = "#F0FDF4";          // Light Mint Tint background

export const STAGES = ["Upload", "Parse", "Index", "Verify"];

export type JobStatus = "queued" | "processing" | "completed" | "failed" | "verified";

export interface Job {
  id: number;
  name: string;
  meta: string;
  stageIndex: number;
  status: JobStatus;
  error?: string;
}