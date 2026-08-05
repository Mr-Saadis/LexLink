import type { JobStatus } from "../../theme/theme";
import { GREEN, MUTED, TEXT } from "../../theme/theme";

interface StatusBadgeProps {
  status: JobStatus | string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusStyles = () => {
    switch (status.toLowerCase()) {
      case "completed":
      case "verified":
        return { bg: "#E6F4EA", color: GREEN, label: status };
      case "processing":
        return { bg: "#E8F0FE", color: "#1A73E8", label: "Processing" };
      case "queued":
        return { bg: "#F1F3F4", color: MUTED, label: "Queued" };
      case "failed":
        return { bg: "#FCE8E6", color: "#D93025", label: "Failed" };
      default:
        return { bg: "#F1F3F4", color: TEXT, label: status };
    }
  };

  const { bg, color, label } = getStatusStyles();

  return (
    <span
      className="px-2.5 py-1 rounded-full text-xs font-medium inline-block capitalize"
      style={{ backgroundColor: bg, color: color }}
    >
      {label}
    </span>
  );
}