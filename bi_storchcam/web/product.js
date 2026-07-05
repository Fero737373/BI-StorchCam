(() => {
  const weather = document.getElementById('weatherText');
  if (!weather) return;

  function span(text, className) {
    const el = document.createElement('span');
    el.className = className;
    el.textContent = text;
    return el;
  }

  function separator() {
    const el = document.createElement('span');
    el.className = 'weather-separator';
    el.textContent = '·';
    el.setAttribute('aria-hidden', 'true');
    return el;
  }

  function renderWeather(raw) {
    const text = String(raw || '').replace(/\s+/g, ' ').trim();
    if (!text || weather.dataset.renderedRaw === text) return;

    const parts = text.split('|').map((part) => part.trim()).filter(Boolean);
    weather.dataset.renderedRaw = text;
    weather.setAttribute('aria-label', text);
    weather.replaceChildren();

    if (parts.length < 2) {
      weather.appendChild(span(text, 'weather-part weather-location'));
      return;
    }

    parts.forEach((part, index) => {
      const className = index === 0
        ? 'weather-part weather-location'
        : index === 1
          ? 'weather-part weather-temp'
          : 'weather-part';
      weather.appendChild(span(part, className));
      if (index < parts.length - 1) weather.appendChild(separator());
    });
  }

  const observer = new MutationObserver(() => {
    if (weather.children.length === 1 && weather.firstElementChild) return;
    renderWeather(weather.textContent);
  });

  renderWeather(weather.textContent);
  observer.observe(weather, { childList: true, characterData: true, subtree: true });
})();
