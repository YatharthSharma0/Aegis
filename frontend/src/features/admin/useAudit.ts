import { useQuery } from "@tanstack/react-query";

import { getAudit, type AuditParams } from "../../api/system";

export function useAudit(params: AuditParams = {}) {
  return useQuery({
    queryKey: ["audit", params],
    queryFn: ({ signal }) => getAudit(params, signal),
  });
}
