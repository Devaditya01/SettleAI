// auth-guard.js — runs before app.js to enforce authentication
// If no Supabase session is found, redirect immediately to login.

(async () => {
  const isDemoMode = !window.SETTLE_CONFIG?.SUPABASE_URL || window.SETTLE_CONFIG.SUPABASE_URL === 'YOUR_SUPABASE_URL';

  if (isDemoMode) {
    // In demo mode without keys, bypass auth guard entirely.
    return;
  }

  const { createClient } = supabase;
  const client = createClient(
    window.SETTLE_CONFIG.SUPABASE_URL,
    window.SETTLE_CONFIG.SUPABASE_ANON_KEY
  );

  const { data: { session } } = await client.auth.getSession();

  if (!session) {
    window.location.replace('/login.html');
  }
})();
