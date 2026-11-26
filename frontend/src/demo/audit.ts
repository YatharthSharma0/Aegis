/** A hash-chained audit log, mirroring `backend/app/security/audit.py` in shape. */
import type { AuditEntryOut, AuditVerificationOut } from "../api/types";
import { sha256Hex } from "./sha256";

export const GENESIS_HASH = "0".repeat(64);

export type AuditFields = Omit<AuditEntryOut, "seq" | "prev_row_hash" | "row_hash">;

function rowHash(prev: string, e: AuditFields): string {
  // A fixed field order keeps the hash stable across a localStorage round trip.
  return sha256Hex(
    JSON.stringify([
      prev, e.ts, e.actor_id, e.actor_role, e.action, e.trace_id, e.case_id,
      e.address, e.chain, e.detail, e.result_hash, e.request_id,
    ]),
  );
}

export function appendAudit(log: AuditEntryOut[], fields: AuditFields): void {
  const last = log[log.length - 1];
  const prev = last?.row_hash ?? GENESIS_HASH;
  log.push({
    ...fields,
    seq: (last?.seq ?? 0) + 1,
    prev_row_hash: prev,
    row_hash: rowHash(prev, fields),
  });
}

export function verifyAudit(log: AuditEntryOut[]): AuditVerificationOut {
  let prev = GENESIS_HASH;
  for (const [i, entry] of log.entries()) {
    if (entry.seq !== i + 1 || entry.prev_row_hash !== prev || entry.row_hash !== rowHash(prev, entry)) {
      return { ok: false, checked: i, broken_at_seq: entry.seq, reason: "hash chain mismatch" };
    }
    prev = entry.row_hash;
  }
  return { ok: true, checked: log.length, broken_at_seq: null, reason: null };
}
