(() => {
  let theme = new URLSearchParams(location.search).get('theme');
  if (!['midnight', 'pearl'].includes(theme)) {
    try { theme = localStorage.getItem('settle-edition'); } catch (_) {}
  }
  const pearl = theme === 'pearl';
  document.documentElement.classList.toggle('pearl', pearl);
  document.querySelectorAll('[data-home]').forEach(link => {
    link.href = pearl ? 'pearl.html' : 'index.html';
  });
})();
