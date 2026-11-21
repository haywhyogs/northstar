// Small wrapper around the payments API. All calls go to /api/... (forwarded to the Python API).

export type Account = {
  account_number: string;
  currency: string;
  balance_cents: number;
  balance: string;
};

export type Transaction = {
  payment_id: string;
  direction: "debit" | "credit";
  amount_cents: number;
  counterparty_account_number: string;
  payment_status: string;
  created_at: string;
};

export type Payment = {
  payment_id: string;
  status: string;
  amount_cents: number;
  to_account_number: string;
  correlation_id: string;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(
  path: string,
  options: { token?: string; method?: string; body?: unknown; headers?: Record<string, string> } = {},
): Promise<{ data: T; headers: Headers }> {
  const response = await fetch(`/api${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...options.headers,
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // Not JSON (e.g. a plain "Internal Server Error"): fall through to the status-based message below.
  }
  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : response.status === 422
          ? "Please check the details you entered."
          : `Something went wrong (error ${response.status}).`;
    throw new ApiError(response.status, message);
  }
  return { data: data as T, headers: response.headers };
}

export const api = {
  login: (email: string, password: string) =>
    call<{ access_token: string }>("/auth/login", { method: "POST", body: { email, password } }),
  account: (token: string) => call<Account>("/accounts/me", { token }),
  transactions: (token: string) => call<Transaction[]>("/accounts/me/transactions?limit=20", { token }),
  // The idempotency key identifies ONE "Send" action. Sending it again can never create a second payment.
  pay: (token: string, idempotencyKey: string, toAccountNumber: string, amountCents: number) =>
    call<Payment>("/payments", {
      token,
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: { to_account_number: toAccountNumber, amount_cents: amountCents },
    }),
};

export function money(cents: number, currency = "CAD"): string {
  return (cents / 100).toLocaleString("en-CA", { style: "currency", currency });
}

// "250" or "250.5" or "250.50" -> 25000 cents, using text (no floating-point rounding). null if invalid.
export function toCents(input: string): number | null {
  const match = input.trim().match(/^(\d{1,7})(?:\.(\d{1,2}))?$/);
  if (!match) return null;
  const cents = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  return cents > 0 ? cents : null;
}
