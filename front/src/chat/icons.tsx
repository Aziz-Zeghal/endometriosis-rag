// Inline icons (no icon library): 24px grid, stroke follows the text colour.
const props = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

export const ChatIcon = () => (
  <svg {...props} width={22} height={22}>
    <path d="M4 5h16v11H9l-5 4z" />
    <path d="M9 10h6" />
  </svg>
);

export const CloseIcon = () => (
  <svg {...props}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

export const SendIcon = () => (
  <svg {...props}>
    <path d="M5 12h13M13 6l6 6-6 6" />
  </svg>
);

export const StopIcon = () => (
  <svg {...props} fill="currentColor" stroke="none">
    <rect x="7" y="7" width="10" height="10" rx="1.5" />
  </svg>
);

export const RetryIcon = () => (
  <svg {...props} width={16} height={16}>
    <path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4h4" />
  </svg>
);

export const ExternalIcon = () => (
  <svg {...props} width={14} height={14}>
    <path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5" />
  </svg>
);

export const InfoIcon = () => (
  <svg {...props} width={16} height={16}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8h.01" />
  </svg>
);

export const AlertIcon = () => (
  <svg {...props} width={16} height={16}>
    <path d="M12 4 2.5 20h19z" />
    <path d="M12 10v4M12 17h.01" />
  </svg>
);

export const HelpIcon = () => (
  <svg {...props} width={16} height={16}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.1M12 17h.01" />
  </svg>
);

export const ShieldIcon = () => (
  <svg {...props} width={16} height={16}>
    <path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6z" />
  </svg>
);

export const BookIcon = () => (
  <svg {...props}>
    {/* Open book: two curved pages meeting at the spine, with text lines. */}
    <path d="M12 7c-2-1.6-5-2-9-1.5v13c4-.5 7-.1 9 1.5 2-1.6 5-2 9-1.5v-13c-4-.5-7-.1-9 1.5z" />
    <path d="M12 7v13M6 9.5h3M6 13h3M15 9.5h3M15 13h3" />
  </svg>
);

export const ChevronIcon = () => (
  <svg {...props} width={18} height={18}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);

export const PhoneIcon = () => (
  <svg {...props}>
    <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z" />
  </svg>
);

export const SmsIcon = () => (
  <svg {...props}>
    <path d="M4 5h16v11H9l-5 4z" />
    <path d="M8 10.5h.01M12 10.5h.01M16 10.5h.01" />
  </svg>
);

export const PlusIcon = () => (
  <svg {...props}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

/** Generic mark drawn for the fictional body (not a real logo): a cross in a rounded square. */
export const Mark = ({ className = "size-10", tone = "accent" }: { className?: string; tone?: "accent" | "paper" }) => (
  <svg viewBox="0 0 32 32" aria-hidden="true" className={`shrink-0 ${className}`}>
    <rect width="32" height="32" rx="9" className={tone === "accent" ? "fill-accent" : "fill-paper"} />
    <path
      d="M16 9v14M9 16h14"
      className={tone === "accent" ? "stroke-accent-ink" : "stroke-accent"}
      strokeWidth="3.5"
      strokeLinecap="round"
    />
  </svg>
);

export const AskIcon = () => (
  <svg {...props} width={22} height={22}>
    <path d="M4 5h16v11H9l-5 4z" />
    <path d="M8.5 9.5h7M8.5 12.5h4" />
  </svg>
);
