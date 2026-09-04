(() => {
  'use strict';

  // Guard: if config.js not loaded, bail with helpful error
  if (!window.SETTLE_CONFIG?.SUPABASE_URL || window.SETTLE_CONFIG.SUPABASE_URL === 'YOUR_SUPABASE_URL') {
    const err = document.getElementById('login-error');
    if (err) {
      err.textContent = 'App not configured: copy config.example.js → config.js and add your Supabase keys.';
      err.classList.add('visible');
    }
    return;
  }

  const { createClient } = supabase;
  const client = createClient(
    window.SETTLE_CONFIG.SUPABASE_URL,
    window.SETTLE_CONFIG.SUPABASE_ANON_KEY
  );

  const form   = document.getElementById('login-form');
  const btn    = document.getElementById('login-btn');
  const errBox = document.getElementById('login-error');

  function setLoading(loading) {
    btn.disabled = loading;
    btn.classList.toggle('loading', loading);
  }

  function showError(msg) {
    errBox.textContent = msg;
    errBox.classList.add('visible');
  }

  function clearError() {
    errBox.textContent = '';
    errBox.classList.remove('visible');
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();
    setLoading(true);

    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    const { data, error } = await client.auth.signInWithPassword({ email, password });

    if (error) {
      showError(error.message || 'Sign-in failed. Please check your credentials.');
      setLoading(false);
      return;
    }

    // Session is stored automatically by Supabase in localStorage
    window.location.href = 'dashboard/index.html';
  });

  // If already signed in, redirect straight to dashboard
  client.auth.getSession().then(({ data: { session } }) => {
    if (session) {
      window.location.replace('dashboard/index.html');
    }
  });
})();
