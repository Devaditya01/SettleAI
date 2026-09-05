// Apply the theme before paint. Browser preference is used until the user chooses one.
(() => {
  const query = new URLSearchParams(location.search).get('theme');
  let saved;
  try { saved = localStorage.getItem('settlelens-edition'); } catch (_) {}
  const explicit = ['midnight', 'pearl'].includes(query) ? query : null;
  const stored = ['midnight', 'pearl'].includes(saved) ? saved : null;
  const system = matchMedia('(prefers-color-scheme: light)').matches ? 'pearl' : 'midnight';
  const edition = explicit || stored || system;
  document.documentElement.dataset.theme = edition;
  function applyTheme(theme, persist = true) {
    document.documentElement.dataset.theme = theme;
    const button = document.getElementById('theme-toggle');
    const next = theme === 'midnight' ? 'Light' : 'Dark';
    button.querySelector('span:last-child').textContent = next;
    button.setAttribute('aria-label', `Switch to ${next} theme`);
    button.title = `Switch to ${next} theme`;
    document.querySelector('meta[name="theme-color"]').content = theme === 'pearl' ? '#eeeae2' : '#11110f';
    document.getElementById('landing-link').href = theme === 'pearl' ? '../pearl.html' : '../index.html';
    if (persist) {
      try { localStorage.setItem('settlelens-edition', theme); } catch (_) {}
    }
  }
  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(edition, false);
    document.getElementById('theme-toggle').addEventListener('click', () => {
      const theme = document.documentElement.dataset.theme === 'midnight' ? 'pearl' : 'midnight';
      applyTheme(theme);
      // Keep an explicit landing-page edition consistent on refresh, too.
      try { const url = new URL(location.href); url.searchParams.set('theme', theme); history.replaceState(null, '', url); } catch (_) {}
    });
    if (!explicit && !stored) {
      matchMedia('(prefers-color-scheme: light)').addEventListener('change', event => {
        applyTheme(event.matches ? 'pearl' : 'midnight', false);
      });
    }
  });
})();
