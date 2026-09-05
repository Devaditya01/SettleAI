(() => {
  let pending;
  window.SettleLensLoadSupabase = () => {
    if (window.supabase) return Promise.resolve(window.supabase);
    if (pending) return pending;

    pending = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      script.async = true;
      script.onload = () => window.supabase
        ? resolve(window.supabase)
        : reject(new Error('Supabase failed to initialize.'));
      script.onerror = () => reject(new Error('Supabase could not be loaded.'));
      document.head.append(script);
    });

    return pending;
  };
})();
