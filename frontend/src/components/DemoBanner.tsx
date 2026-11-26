import { useQueryClient } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { useNavigate } from "react-router-dom";

/** Says plainly that nothing on screen is real, and offers a clean slate. */
export function DemoBanner() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const reset = async () => {
    const { resetDemoState } = await import("../demo/store");
    resetDemoState();
    queryClient.clear();
    navigate("/");
  };

  return (
    <div
      role="note"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-warning/40 bg-warning/10 px-4 py-2 text-xs text-secondary sm:px-6"
    >
      <FlaskConical size={14} className="text-warning" aria-hidden />
      <span className="flex-1">
        Showcase mode — every case, address and exchange is synthetic sample data
        stored in this browser.
      </span>
      <button onClick={reset} className="text-link hover:underline">
        Reset demo data
      </button>
    </div>
  );
}
