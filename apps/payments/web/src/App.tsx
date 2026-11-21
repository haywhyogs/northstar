import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Account, ApiError, api, money, toCents, Transaction } from "./api";

export default function App() {
  // The login token lives only in memory: refreshing the page signs you out (nothing stored in the browser).
  const [token, setToken] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <span className="logo">★</span> Northstar Bank
        </div>
        <span className="badge">Demo · synthetic data only</span>
        {token && (
          <button className="link" onClick={() => setToken(null)}>
            Sign out
          </button>
        )}
      </header>
      {token ? (
        <Dashboard
          token={token}
          onExpired={() => {
            setToken(null);
            setNotice("Your session expired. Please sign in again.");
          }}
        />
      ) : (
        <Login
          notice={notice}
          onSignedIn={(t) => {
            setNotice(null);
            setToken(t);
          }}
        />
      )}
    </div>
  );
}

function Login({ notice, onSignedIn }: { notice: string | null; onSignedIn: (token: string) => void }) {
  const [email, setEmail] = useState("customer0001@northstar.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.login(email, password);
      onSignedIn(data.access_token);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Can't reach the bank right now. Is the API running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="center">
      <form className="card narrow" onSubmit={submit}>
        <h1>Sign in</h1>
        {notice && <p className="info">{notice}</p>}
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="hint">
          Demo customers: <code>customer0001@northstar.test</code> to <code>customer0300@northstar.test</code>.
        </p>
      </form>
    </main>
  );
}

function Dashboard({ token, onExpired }: { token: string; onExpired: () => void }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) onExpired();
      else setError(e instanceof ApiError ? e.message : "Can't reach the bank right now.");
    },
    [onExpired],
  );

  const load = useCallback(async () => {
    try {
      const [a, t] = await Promise.all([api.account(token), api.transactions(token)]);
      setAccount(a.data);
      setTransactions(t.data);
      setError(null);
    } catch (e) {
      handleError(e);
    }
  }, [token, handleError]);

  useEffect(() => {
    load();
  }, [load]);

  // While any payment is still pending, check again every 5 seconds so you can watch it complete.
  const anyPending = transactions.some((t) => t.payment_status === "pending" || t.payment_status === "processing");
  useEffect(() => {
    if (!anyPending) return;
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [anyPending, load]);

  return (
    <main className="grid">
      <section className="card balance">
        <h2>Your account</h2>
        {account ? (
          <>
            <p className="muted">Account number {account.account_number}</p>
            <p className="amount">{money(account.balance_cents, account.currency)}</p>
            <p className="muted">Available balance</p>
          </>
        ) : (
          <p className="muted">Loading…</p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <SendMoney token={token} onSent={load} onError={handleError} />

      <section className="card wide">
        <div className="row">
          <h2>Recent activity</h2>
          <button className="link" onClick={load}>
            Refresh
          </button>
        </div>
        {transactions.length === 0 ? (
          <p className="muted">No payments yet.</p>
        ) : (
          <ul className="activity">
            {transactions.map((t) => (
              <li key={`${t.payment_id}-${t.direction}`}>
                <div>
                  <strong>{t.direction === "debit" ? "Sent to" : "Received from"}</strong>{" "}
                  {t.counterparty_account_number}
                  <div className="muted small">{new Date(t.created_at + "Z").toLocaleString()}</div>
                </div>
                <div className="right">
                  <span className={t.direction === "debit" ? "out" : "in"}>
                    {t.direction === "debit" ? "−" : "+"}
                    {money(t.amount_cents)}
                  </span>
                  <span className={`status ${t.payment_status}`}>{t.payment_status}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function SendMoney({
  token,
  onSent,
  onError,
}: {
  token: string;
  onSent: () => void;
  onError: (e: unknown) => void;
}) {
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  // One key per "Send" action. Kept if the request fails, so retrying the SAME payment can't charge twice.
  const keyRef = useRef<string | null>(null);

  const cents = toCents(amount);
  const ready = to.trim().length > 0 && cents !== null && !busy;

  function edited(update: () => void) {
    keyRef.current = null; // different details = a different payment = a new key
    setMessage(null);
    setProblem(null);
    update();
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!ready || cents === null) return;
    keyRef.current ??= crypto.randomUUID();
    setBusy(true);
    setProblem(null);
    try {
      const { data } = await api.pay(token, keyRef.current, to.trim(), cents);
      setMessage(`${money(data.amount_cents)} to ${data.to_account_number} is ${data.status}.`);
      keyRef.current = null;
      setTo("");
      setAmount("");
      onSent();
    } catch (e) {
      if (e instanceof ApiError && e.status !== 401) setProblem(e.message);
      else onError(e);
    } finally {
      setBusy(false);
    }
  }

  // Demo of guard #1: fire the SAME request twice at once, as a double-click or network retry would.
  async function sendTwice() {
    if (!ready || cents === null) return;
    const key = crypto.randomUUID();
    setBusy(true);
    setProblem(null);
    const results = await Promise.allSettled([
      api.pay(token, key, to.trim(), cents),
      api.pay(token, key, to.trim(), cents),
    ]);
    setBusy(false);
    const ok = results.filter((r) => r.status === "fulfilled");
    if (ok.length === 0) {
      const first = results[0];
      if (first.status === "rejected") {
        if (first.reason instanceof ApiError && first.reason.status !== 401) setProblem(first.reason.message);
        else onError(first.reason);
      }
      return;
    }
    const ids = new Set(ok.map((r) => (r as PromiseFulfilledResult<{ data: { payment_id: string } }>).value.data.payment_id));
    setMessage(`Sent the same request twice → ${ids.size} payment created, charged once.`);
    setTo("");
    setAmount("");
    onSent();
  }

  return (
    <form className="card" onSubmit={send}>
      <h2>Send money</h2>
      <label>
        Recipient account number
        <input value={to} placeholder="e.g. NS0000000002" onChange={(e) => edited(() => setTo(e.target.value))} />
      </label>
      <label>
        Amount (CAD)
        <input
          value={amount}
          inputMode="decimal"
          placeholder="250.00"
          onChange={(e) => edited(() => setAmount(e.target.value))}
        />
      </label>
      {amount && cents === null && <p className="error">Enter an amount like 250 or 250.00</p>}
      {problem && <p className="error">{problem}</p>}
      {message && <p className="success">{message}</p>}
      <button className="primary" disabled={!ready}>
        {busy ? "Sending…" : "Send"}
      </button>
      <button type="button" className="secondary" disabled={!ready} onClick={sendTwice}>
        Demo: double-click (send twice)
      </button>
    </form>
  );
}
