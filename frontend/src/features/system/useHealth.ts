import { useQuery } from "@tanstack/react-query";

import { ApiError } from "../../api/client";
import { getHealth } from "../../api/system";

/** Background heartbeat. `offline` is true only once a request has actually
 * failed to reach the backend — not while the first check is in flight. */
export function useHealth() {
  const q = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 20_000,
    refetchOnWindowFocus: true,
    retry: false,
    staleTime: 10_000,
  });

  const offline =
    q.isError &&
    (!(q.error instanceof ApiError) ||
      q.error.code === "backend_unavailable" ||
      q.error.status >= 500);

  return { ...q, offline };
}
