import { useRef, useState } from "react";

interface Props {
  summary: string;
  symbol: string;
  loading: boolean;
}

export function Assistant({ summary, symbol, loading }: Props) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ x: 24, y: 88 });
  const drag = useRef<{ dx: number; dy: number } | null>(null);

  return (
    <>
      <button className="ai-fab" onClick={() => setOpen((value) => !value)}>AI</button>
      {open ? (
        <section
          className="ai-panel"
          style={{ right: position.x, bottom: position.y }}
          onPointerDown={(event) => {
            if ((event.target as HTMLElement).dataset.drag !== "handle") return;
            drag.current = { dx: event.clientX, dy: event.clientY };
            const start = position;
            const move = (next: PointerEvent) => {
              if (!drag.current) return;
              setPosition({
                x: Math.max(16, start.x - (next.clientX - drag.current.dx)),
                y: Math.max(72, start.y - (next.clientY - drag.current.dy)),
              });
            };
            const up = () => {
              drag.current = null;
              window.removeEventListener("pointermove", move);
              window.removeEventListener("pointerup", up);
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up);
          }}
        >
          <header data-drag="handle">Market structure · {symbol}</header>
          <p>{loading ? "Calculating structure..." : summary || "No summary yet."}</p>
          <small>Technical structure only. Not financial advice.</small>
        </section>
      ) : null}
    </>
  );
}
