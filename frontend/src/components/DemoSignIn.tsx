import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "../demo/accounts";
import { Button } from "../ui/Button";

/** One-click sign-in for showcasing; no backend account is needed. */
export function DemoSignIn({
  disabled,
  onSelect,
}: {
  disabled: boolean;
  onSelect: (email: string, password: string) => void;
}) {
  return (
    <div className="mt-4 border-t border-subtle pt-4">
      <p className="mb-2 text-xs text-muted">
        Demo mode — sample data, no server. Choose an account:
      </p>
      <div className="flex flex-col gap-2">
        {DEMO_ACCOUNTS.map((a) => (
          <Button
            key={a.id}
            type="button"
            variant="secondary"
            disabled={disabled}
            onClick={() => onSelect(a.email, DEMO_PASSWORD)}
          >
            Continue as {a.role === "admin" ? "administrator (with audit log)" : "investigating officer"}
          </Button>
        ))}
      </div>
    </div>
  );
}
