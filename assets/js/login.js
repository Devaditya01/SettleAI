(() => {
  'use strict';

  const isDemoMode = !window.SETTLE_CONFIG?.SUPABASE_URL || window.SETTLE_CONFIG.SUPABASE_URL === 'YOUR_SUPABASE_URL';

  let client = null;
  if (!isDemoMode) {
    const { createClient } = supabase;
    client = createClient(
      window.SETTLE_CONFIG.SUPABASE_URL,
      window.SETTLE_CONFIG.SUPABASE_ANON_KEY
    );
  }

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

    if (isDemoMode) {
      setTimeout(() => {
        window.location.href = '/dashboard/index.html';
      }, 600);
      return;
    }

    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    const { data, error } = await client.auth.signInWithPassword({ email, password });

    if (error) {
      showError(error.message || 'Sign-in failed. Please check your credentials.');
      setLoading(false);
      return;
    }

    window.location.href = '/dashboard/index.html';
  });

  // If already signed in, redirect straight to dashboard.
  if (!isDemoMode) {
    client.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        window.location.replace('/dashboard/index.html');
      }
    });
  }

  const googleBtn = document.getElementById('google-btn');
  if (googleBtn) {
    googleBtn.addEventListener('click', async () => {
      clearError();
      if (isDemoMode) {
        window.location.href = '/dashboard/index.html';
        return;
      }

      const { data, error } = await client.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: window.location.origin + '/dashboard/index.html'
        }
      });
      if (error) {
        showError(error.message || 'Google sign-in failed.');
      }
    });
  }
})();
