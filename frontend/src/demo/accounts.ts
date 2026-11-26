import type { MeResponse } from "../api/types";

export const DEMO_PASSWORD = "demo-password";

export const DEMO_ACCOUNTS: MeResponse[] = [
  {
    id: "demo-officer", email: "officer@demo.aegis", full_name: "Demo Officer",
    role: "officer", unit: "Sample Cyber Cell",
  },
  {
    id: "demo-admin", email: "admin@demo.aegis", full_name: "Demo Administrator",
    role: "admin", unit: "Sample Cyber Cell",
  },
];
