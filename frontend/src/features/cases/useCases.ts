import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  addComplaint,
  createCase,
  getCase,
  listCases,
  updateCase,
  type ListCasesParams,
} from "../../api/cases";
import type {
  AddComplaintRequest,
  CreateCaseRequest,
  UpdateCaseRequest,
} from "../../api/types";

const keys = {
  all: ["cases"] as const,
  list: (p: ListCasesParams) => ["cases", "list", p] as const,
  detail: (id: string) => ["cases", "detail", id] as const,
};

export function useCases(params: ListCasesParams = {}) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: ({ signal }) => listCases(params, signal),
  });
}

export function useCase(id: string) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: ({ signal }) => getCase(id, signal),
    enabled: id !== "",
  });
}

export function useCreateCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateCaseRequest) => createCase(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all }),
  });
}

export function useUpdateCase(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateCaseRequest) => updateCase(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all }),
  });
}

export function useAddComplaint(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AddComplaintRequest) => addComplaint(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.detail(id) }),
  });
}
