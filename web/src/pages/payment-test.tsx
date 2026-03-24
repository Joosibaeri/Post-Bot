import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useAuth, useUser } from '@clerk/nextjs';
import SEOHead from '@/components/SEOHead';
import ThemeToggle from '@/components/ThemeToggle';

type CheckoutResponse = {
  session_id: string;
  checkout_url: string;
};

type SubscriptionResponse = {
  has_subscription: boolean;
  status: string | null;
  plan_id: string | null;
  current_period_end: number | null;
  cancel_at_period_end: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PaymentTestPage() {
  const { user, isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();

  const [monthlyPlanCode, setMonthlyPlanCode] = useState('');
  const [yearlyPlanCode, setYearlyPlanCode] = useState('');
  const [email, setEmail] = useState('');
  const [amountKobo, setAmountKobo] = useState('500000');
  const [successUrl, setSuccessUrl] = useState('');
  const [cancelUrl, setCancelUrl] = useState('');
  const [isLoadingCheckout, setIsLoadingCheckout] = useState(false);
  const [isLoadingSubscription, setIsLoadingSubscription] = useState(false);
  const [checkoutResult, setCheckoutResult] = useState<CheckoutResponse | null>(null);
  const [subscriptionResult, setSubscriptionResult] = useState<SubscriptionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const userId = user?.id || '';

  useMemo(() => {
    if (!isLoaded || !user) {
      return;
    }
    if (!email) {
      setEmail(user.primaryEmailAddress?.emailAddress || '');
    }
    if (!successUrl) {
      setSuccessUrl('http://localhost:3000/dashboard?payment=success');
    }
    if (!cancelUrl) {
      setCancelUrl('http://localhost:3000/pricing');
    }
  }, [cancelUrl, email, isLoaded, successUrl, user]);

  const createCheckout = async (planCode?: string) => {
    const hasPlan = !!planCode?.trim();
    const parsedAmount = amountKobo.trim() ? Number.parseInt(amountKobo.trim(), 10) : NaN;
    const hasAmount = Number.isFinite(parsedAmount) && parsedAmount >= 100;

    if (!hasPlan && !hasAmount) {
      setError('Enter a plan code or a valid amount in kobo (minimum 100).');
      return;
    }

    setIsLoadingCheckout(true);
    setCheckoutResult(null);
    setError(null);

    try {
      const token = await getToken();
      if (!token || !userId) {
        setError('Sign in first to test checkout.');
        return;
      }

      const response = await fetch(`${API_BASE}/api/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: userId,
          price_id: hasPlan ? planCode?.trim() : undefined,
          amount_kobo: hasAmount ? parsedAmount : undefined,
          email: email.trim() || undefined,
          success_url: successUrl.trim() || undefined,
          cancel_url: cancelUrl.trim() || undefined,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.detail || `Checkout failed (${response.status})`);
      }

      const data = (await response.json()) as CheckoutResponse;
      setCheckoutResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Checkout request failed');
    } finally {
      setIsLoadingCheckout(false);
    }
  };

  const checkSubscription = async () => {
    setIsLoadingSubscription(true);
    setSubscriptionResult(null);
    setError(null);

    try {
      const token = await getToken();
      if (!token || !userId) {
        setError('Sign in first to check subscription.');
        return;
      }

      const response = await fetch(`${API_BASE}/api/subscription`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.detail || `Subscription check failed (${response.status})`);
      }

      const data = (await response.json()) as SubscriptionResponse;
      setSubscriptionResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Subscription check failed');
    } finally {
      setIsLoadingSubscription(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-slate-100 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
      <SEOHead
        title="Payment Test - Post Bot"
        description="Manual UI for testing Paystack checkout and subscription endpoints."
      />

      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-slate-700 dark:text-slate-200 font-semibold hover:text-blue-600 dark:hover:text-blue-400">
            Back to Home
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-10">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-lg p-6 md:p-8 space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Payment Test UI</h1>
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              Use this page to test checkout initialization and subscription status responses.
            </p>
          </div>

          {!isLoaded && <p className="text-slate-600 dark:text-slate-300">Loading user...</p>}

          {isLoaded && !isSignedIn && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-700 p-4">
              <p className="text-amber-900 dark:text-amber-200">Sign in first. This test page calls authenticated payment endpoints.</p>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">User ID</span>
              <input
                value={userId}
                disabled
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Email</span>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </label>

            <label className="block md:col-span-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Success URL</span>
              <input
                value={successUrl}
                onChange={(e) => setSuccessUrl(e.target.value)}
                placeholder="https://your-frontend-url/dashboard?payment=success"
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </label>

            <label className="block md:col-span-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Cancel URL</span>
              <input
                value={cancelUrl}
                onChange={(e) => setCancelUrl(e.target.value)}
                placeholder="https://your-frontend-url/pricing"
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </label>

            <label className="block md:col-span-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Amount Override (kobo)</span>
              <input
                value={amountKobo}
                onChange={(e) => setAmountKobo(e.target.value)}
                placeholder="500000"
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Example: 500000 = NGN 5000. Use this when Paystack rejects plan amount.
              </p>
            </label>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-3">
              <h2 className="font-semibold text-slate-800 dark:text-slate-100">Monthly Plan Checkout</h2>
              <input
                value={monthlyPlanCode}
                onChange={(e) => setMonthlyPlanCode(e.target.value)}
                placeholder="PLN_xxxxx"
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
              <button
                onClick={() => createCheckout(monthlyPlanCode)}
                disabled={!isSignedIn || isLoadingCheckout}
                className="w-full rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white px-4 py-2 font-medium"
              >
                {isLoadingCheckout ? 'Creating Checkout...' : 'Create Monthly Checkout'}
              </button>
            </div>

            <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-3">
              <h2 className="font-semibold text-slate-800 dark:text-slate-100">Yearly Plan Checkout</h2>
              <input
                value={yearlyPlanCode}
                onChange={(e) => setYearlyPlanCode(e.target.value)}
                placeholder="PLN_xxxxx"
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
              <button
                onClick={() => createCheckout(yearlyPlanCode)}
                disabled={!isSignedIn || isLoadingCheckout}
                className="w-full rounded-lg bg-violet-600 hover:bg-violet-700 disabled:bg-slate-400 text-white px-4 py-2 font-medium"
              >
                {isLoadingCheckout ? 'Creating Checkout...' : 'Create Yearly Checkout'}
              </button>
            </div>
          </div>

          <div>
            <button
              onClick={() => createCheckout()}
              disabled={!isSignedIn || isLoadingCheckout}
              className="rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white px-4 py-2 font-medium"
            >
              {isLoadingCheckout ? 'Creating Checkout...' : 'Create Amount-only Checkout'}
            </button>
          </div>

          <div>
            <button
              onClick={checkSubscription}
              disabled={!isSignedIn || isLoadingSubscription}
              className="rounded-lg bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white px-4 py-2 font-medium"
            >
              {isLoadingSubscription ? 'Checking Subscription...' : 'Check Subscription Status'}
            </button>
          </div>

          {error && (
            <div className="rounded-lg border border-red-300 bg-red-50 dark:bg-red-950/30 dark:border-red-800 p-3 text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          {checkoutResult && (
            <div className="rounded-lg border border-green-300 bg-green-50 dark:bg-green-950/30 dark:border-green-800 p-4 space-y-2">
              <p className="text-green-800 dark:text-green-200 font-medium">Checkout initialized</p>
              <p className="text-sm text-green-700 dark:text-green-300">Session: {checkoutResult.session_id}</p>
              <a
                href={checkoutResult.checkout_url}
                target="_blank"
                rel="noreferrer"
                className="inline-block mt-2 rounded-lg bg-green-600 hover:bg-green-700 text-white px-4 py-2"
              >
                Open Paystack Checkout
              </a>
            </div>
          )}

          {subscriptionResult && (
            <div className="rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-4">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100 mb-2">Subscription Response</h3>
              <pre className="text-xs text-slate-700 dark:text-slate-300 overflow-auto">
                {JSON.stringify(subscriptionResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
