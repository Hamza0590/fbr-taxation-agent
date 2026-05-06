// Minimal icon set — inline SVG, single-stroke style
const Icon = ({ name, size = 16, ...p }) => {
  const s = size;
  const common = { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", ...p };
  const paths = {
    plus: <><path d="M12 5v14M5 12h14"/></>,
    chat: <><path d="M21 12a8 8 0 0 1-11.5 7.2L4 21l1.8-5.5A8 8 0 1 1 21 12Z"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/></>,
    arrow: <><path d="M5 12h14M13 5l7 7-7 7"/></>,
    send: <><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z"/></>,
    mic: <><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M19 11a7 7 0 1 1-14 0M12 18v3"/></>,
    paperclip: <><path d="M21.4 11.1 12.3 20.2a5 5 0 0 1-7-7L14.3 4a3.3 3.3 0 0 1 4.7 4.7l-9 9a1.7 1.7 0 1 1-2.3-2.3l8-8"/></>,
    download: <><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></>,
    share: <><circle cx="6" cy="12" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="m8.6 10.5 6.8-3.5M8.6 13.5l6.8 3.5"/></>,
    copy: <><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></>,
    logout: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l-5-5 5-5M5 12h12"/></>,
    chevR: <><path d="m9 6 6 6-6 6"/></>,
    chevL: <><path d="m15 6-6 6 6 6"/></>,
    chevD: <><path d="m6 9 6 6 6-6"/></>,
    close: <><path d="M6 6l12 12M18 6 6 18"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 8h0M12 12v4"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>,
    moon: <><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></>,
    pdf: <><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-7-7Z"/><path d="M13 2v7h7"/></>,
    brain: <><path d="M15 5a3 3 0 1 0-5-2.2A3 3 0 0 0 6 5v1a3 3 0 0 0 .5 5.5A3 3 0 0 0 9 17a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 2.5-5.5A3 3 0 0 0 18 6V5a3 3 0 0 0-3-3Z"/></>,
    flask: <><path d="M9 3h6M10 3v6L4 19a2 2 0 0 0 1.7 3h12.6a2 2 0 0 0 1.7-3L14 9V3"/></>,
    book: <><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v18H6.5A2.5 2.5 0 0 0 4 22.5ZM4 4.5v18"/></>,
    eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></>,
    eyeOff: <><path d="M17.9 17.9A10 10 0 0 1 12 19c-6 0-10-7-10-7a17.7 17.7 0 0 1 5.1-5.9M9.9 4.2A10 10 0 0 1 12 4c6 0 10 7 10 7a17.8 17.8 0 0 1-2.3 3.1M3 3l18 18"/><circle cx="12" cy="12" r="3"/></>,
    zap: <><path d="m13 2-8 12h7l-1 8 8-12h-7l1-8Z"/></>,
    x: <><path d="M6 6l12 12M18 6 6 18"/></>,
    table: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16M15 4v16"/></>,
    upload: <><path d="M12 21V9M7 14l5-5 5 5M5 3h14"/></>,
  };
  return <svg {...common}>{paths[name]}</svg>;
};
window.Icon = Icon;
