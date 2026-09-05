// auth-guard.js — runs before app.js to enforce authentication
// If no Supabase session is found, redirect immediately to login.

(async () => {
  const authConfig = window.SETTLELENS_CONFIG || window.SETTLE_CONFIG;
  const isDemoMode = !authConfig?.SUPABASE_URL || authConfig.SUPABASE_URL === 'YOUR_SUPABASE_URL';

  if (isDemoMode) {
    // In demo mode without keys, bypass auth guard entirely.
    return;
  }

  let client;
  try {
    const { createClient } = await window.SettleLensLoadSupabase();
    client = createClient(authConfig.SUPABASE_URL, authConfig.SUPABASE_ANON_KEY);
  } catch (_) {
    window.location.replace('/login.html?auth=unavailable');
    return;
  }

  const { data: { session } } = await client.auth.getSession();

  if (!session) {
    window.location.replace('/login.html');
  }
})();
