(() => {
  'use strict';

  const authConfig = window.SETTLELENS_CONFIG || window.SETTLE_CONFIG;
  const isDemoMode = !authConfig?.SUPABASE_URL || authConfig.SUPABASE_URL === 'YOUR_SUPABASE_URL';

  const clientPromise = isDemoMode ? null : window.SettleLensLoadSupabase().then(({ createClient }) => createClient(
    authConfig.SUPABASE_URL,
    authConfig.SUPABASE_ANON_KEY
  ));

  const form   = document.getElementById('login-form');
  const btn    = document.getElementById('login-btn');
  const errBox = document.getElementById('login-error');

  if (isDemoMode) btn.querySelector('.btn-label').textContent = 'Open workspace ↗';

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

    if (!form.reportValidity()) {
      setLoading(false);
      return;
    }

    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    let client;
    try {
      client = await clientPromise;
    } catch (_) {
      showError('Authentication service is unavailable. Please try again.');
      setLoading(false);
      return;
    }
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
    clientPromise.then(client => client.auth.getSession()).then(({ data: { session } }) => {
      if (session) {
        window.location.replace('/dashboard/index.html');
      }
    }).catch(() => showError('Authentication service is unavailable. Please try again.'));
  }

  const googleBtn = document.getElementById('google-btn');
  if (googleBtn) {
    googleBtn.addEventListener('click', async () => {
      clearError();
      if (isDemoMode) {
        window.location.href = '/dashboard/index.html';
        return;
      }
      let client;
      try {
        client = await clientPromise;
      } catch (_) {
        showError('Authentication service is unavailable. Please try again.');
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
