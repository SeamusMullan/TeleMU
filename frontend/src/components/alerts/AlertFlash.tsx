/** Full-screen flash overlay that briefly appears when a visual alert fires. */

import { useEffect, useRef } from "react";
import { useAlertStore } from "../../stores/alertStore";

export default function AlertFlash() {
  const flashColor = useAlertStore((s) => s.flashColor);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!flashColor || !ref.current) return;
    ref.current.style.opacity = "0.35";
    const t = setTimeout(() => {
      if (ref.current) ref.current.style.opacity = "0";
    }, 150);
    return () => clearTimeout(t);
  }, [flashColor]);

  return (
    <div
      ref={ref}
      className="pointer-events-none fixed inset-0 z-50 transition-opacity duration-700"
      style={{
        backgroundColor: flashColor ?? "transparent",
        opacity: 0,
      }}
      aria-hidden="true"
    />
  );
}
