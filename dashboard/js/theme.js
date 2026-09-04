// Apply the edition before paint. The demo also works when browser storage is blocked.
(() => {
  const query = new URLSearchParams(location.search).get('theme');
  let saved;
  try { saved = localStorage.getItem('settle-edition'); } catch (_) {}
  const edition = ['midnight', 'pearl'].includes(query) ? query : saved === 'pearl' ? 'pearl' : 'midnight';
  document.documentElement.dataset.theme = edition;
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const button = document.getElementById('theme-toggle');
    const next = theme === 'midnight' ? 'Pearl' : 'Midnight';
    button.querySelector('span:last-child').textContent = next;
    button.setAttribute('aria-label', `Switch to ${next} theme`);
    button.title = `Switch to ${next} theme`;
    document.querySelector('meta[name="theme-color"]').content = theme === 'pearl' ? '#eeeae2' : '#11110f';
    document.getElementById('landing-link').href = theme === 'pearl' ? '../pearl.html' : '../index.html';
    try { localStorage.setItem('settle-edition', theme); } catch (_) {}
  }
  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(edition);
    document.getElementById('theme-toggle').addEventListener('click', () => {
      const theme = document.documentElement.dataset.theme === 'midnight' ? 'pearl' : 'midnight';
      applyTheme(theme);
      // Keep an explicit landing-page edition consistent on refresh, too.
      try { const url = new URL(location.href); url.searchParams.set('theme', theme); history.replaceState(null, '', url); } catch (_) {}
    });
  });
})();
