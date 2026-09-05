(() => {
  let saved;
  try { saved = localStorage.getItem('settlelens-edition'); } catch (_) {}

  const useLight = saved
    ? saved === 'pearl'
    : window.matchMedia('(prefers-color-scheme: light)').matches;
  const page = location.pathname.split('/').pop() || 'index.html';

  if (page === 'index.html' && useLight) {
    location.replace(`pearl.html${location.hash}`);
    return;
  }
  if (page === 'pearl.html' && !useLight) {
    location.replace(`index.html${location.hash}`);
    return;
  }

  document.documentElement.classList.toggle('pearl', useLight);
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = useLight ? '#eeeae2' : '#11110f';
})();
