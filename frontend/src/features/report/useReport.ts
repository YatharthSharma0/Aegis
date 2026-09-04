import { useMutation, useQuery } from "@tanstack/react-query";

import {
  createSahyogNotice,
  getReport,
  type SahyogNoticeParams,
} from "../../api/report";

export function useReport(id: string) {
  return useQuery({
    queryKey: ["trace", id, "report"],
    queryFn: ({ signal }) => getReport(id, signal),
    enabled: id !== "",
  });
}

export function useSahyogNotice(id: string) {
  return useMutation({
    mutationFn: (params: SahyogNoticeParams) => createSahyogNotice(id, params),
  });
}
