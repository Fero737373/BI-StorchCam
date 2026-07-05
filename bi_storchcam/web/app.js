let currentConfig = null;
let lastRadarRefresh = 0;
let radarRefreshInFlight = false;
let toastTimer = null;

function byId(id){ return document.getElementById(id); }
function safeArray(value){ return Array.isArray(value) ? value : []; }

function setText(id, text){
  const el = byId(id);
  if(el){ el.textContent = text; }
}

function setStatus(message, state){
  const el = byId('saveState');
  if(!el){ return; }
  el.textContent = message || '';
  if(state){ el.dataset.state = state; }
  else{ delete el.dataset.state; }
}

function showToast(message, state){
  const toast = byId('toast');
  if(!toast || !message){ return; }
  toast.textContent = message;
  toast.dataset.state = state || 'info';
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add('hidden'), 4200);
}

function tick(){
  const d = new Date();
  setText('clock', d.toLocaleTimeString('de-DE', {hour:'2-digit', minute:'2-digit', second:'2-digit'}));
}
setInterval(tick, 1000); tick();

function makeCell(text, cls){
  const td = document.createElement('td');
  td.textContent = text;
  if(cls){ td.className = cls; }
  return td;
}

function renderBoards(boards){
  const root = byId('boards');
  if(!root){ return; }
  root.replaceChildren();

  (boards || []).forEach(board => {
    const card = document.createElement('div');
    card.className = 'board';

    const h = document.createElement('h3');
    h.textContent = board.title || 'HALT';
    card.appendChild(h);

    const table = document.createElement('table');
    const head = document.createElement('thead');
    const hr = document.createElement('tr');
    ['Linie','Ziel','Zeit'].forEach((x,i) => {
      const th = document.createElement('th');
      th.textContent = x;
      if(i === 2){ th.className = 'time'; }
      hr.appendChild(th);
    });
    head.appendChild(hr);
    table.appendChild(head);

    const body = document.createElement('tbody');
    if(board.rows && board.rows.length){
      board.rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.appendChild(makeCell(row.line || '-'));
        tr.appendChild(makeCell(row.target || '-', 'target'));
        tr.appendChild(makeCell(row.mins || '-', 'time'));
        body.appendChild(tr);
      });
    } else {
      const tr = document.createElement('tr');
      const td = makeCell('keine Abfahrten', 'empty');
      td.colSpan = 3;
      tr.appendChild(td);
      body.appendChild(tr);
    }

    table.appendChild(body);
    card.appendChild(table);
    root.appendChild(card);
  });
}

function applyUi(cfg){
  const ui = (cfg && cfg.ui) || {};
  document.body.classList.toggle('hide-weather', !(ui.weather && ui.weather.enabled));
  document.body.classList.toggle('hide-radar', !(ui.radar && ui.radar.enabled));
  document.body.classList.toggle('hide-transit', !(ui.transit && ui.transit.enabled));
  document.body.classList.toggle('hide-system', !(ui.system && ui.system.enabled));

  const radar = byId('radar');
  if(radar && ui.radar && ui.radar.height){
    const height = Math.max(120, Math.min(420, Number(ui.radar.height) || 180));
    radar.style.height = height + 'px';
  }
}

function lon2tile(lon, zoom){
  return Math.floor((lon + 180) / 360 * Math.pow(2, zoom));
}

function lat2tile(lat, zoom){
  const rad = lat * Math.PI / 180;
  return Math.floor((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2 * Math.pow(2, zoom));
}

function replaceTileVars(template, zoom, x, y){
  return template
    .replaceAll('{z}', String(zoom))
    .replaceAll('{x}', String(x))
    .replaceAll('{y}', String(y));
}

function setRadarStatus(text){
  const map = byId('radar-map');
  if(!map){ return; }
  let status = map.querySelector('.radar-status');
  if(!status){
    status = document.createElement('div');
    status.className = 'radar-status';
    map.appendChild(status);
  }
  status.textContent = text;
}

function renderRadar(meta){
  const map = byId('radar-map');
  if(!map){ return; }
  map.replaceChildren();

  const label = meta && meta.label ? meta.label : 'Bielefeld';
  setText('radarLabel', label);

  if(!meta || !meta.ok || !meta.tile_url){
    map.classList.add('radar-offline');
    const error = (meta && meta.error) ? meta.error : 'keine Daten';
    setRadarStatus('offline · ' + error);
    return;
  }

  map.classList.remove('radar-offline');
  const zoom = Number(meta.zoom || 10);
  const lat = Number(meta.latitude || 52.0302);
  const lon = Number(meta.longitude || 8.5325);
  const centerX = lon2tile(lon, zoom);
  const centerY = lat2tile(lat, zoom);

  const grid = document.createElement('div');
  grid.className = 'radar-grid';

  for(let dy = -1; dy <= 1; dy++){
    for(let dx = -1; dx <= 1; dx++){
      const x = centerX + dx;
      const y = centerY + dy;
      const cell = document.createElement('div');
      cell.className = 'radar-cell';

      const base = document.createElement('img');
      base.alt = '';
      base.loading = 'lazy';
      base.decoding = 'async';
      base.src = `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`;

      const rain = document.createElement('img');
      rain.alt = '';
      rain.loading = 'lazy';
      rain.decoding = 'async';
      rain.className = 'rain';
      rain.src = replaceTileVars(meta.tile_url, zoom, x, y);

      cell.appendChild(base);
      cell.appendChild(rain);
      grid.appendChild(cell);
    }
  }

  map.appendChild(grid);
  setRadarStatus(label + ' · aktuell');
}

async function refreshRadar(force){
  const ui = currentConfig && currentConfig.ui ? currentConfig.ui : {};
  if(ui.radar && ui.radar.enabled === false){ return; }

  const now = Date.now();
  const refreshSeconds = ui.radar && ui.radar.refresh_seconds ? Number(ui.radar.refresh_seconds) : 300;
  const interval = Math.max(refreshSeconds, 60) * 1000;
  if(!force && now - lastRadarRefresh < interval){ return; }
  if(radarRefreshInFlight){ return; }

  radarRefreshInFlight = true;
  try{
    const r = await fetch('/api/radar?_=' + now, {cache:'no-store'});
    const d = await r.json();
    renderRadar(d);
    lastRadarRefresh = Date.now();
  }catch(e){
    renderRadar({ok:false, error:e.message || 'Netzwerkfehler'});
    lastRadarRefresh = Date.now();
  }finally{
    radarRefreshInFlight = false;
  }
}

async function pull(){
  try{
    const r = await fetch('/api/state?_=' + Date.now(), {cache:'no-store'});
    const d = await r.json();
    const cfg = d.config || {};
    currentConfig = cfg;
    applyUi(cfg);

    const stream = (cfg.stream && cfg.stream.url) || '';
    const live = byId('live');
    if(stream && live && live.src !== stream){ live.src = stream; }

    const s = d.system || {};
    setText('sys', 'IP ' + (s.ip || '--') + ' | CPU ' + (s.cpu ?? '--') + '% | RAM ' + (s.ram ?? '--') + '% | Temp ' + (s.temp ?? '--') + '°C | Laufzeit ' + (s.uptime || '--'));

    const w = d.weather || {};
    setText('weatherText', w.text || 'Wetter lädt ...');
    renderBoards(d.boards || []);
    refreshRadar(false);
  }catch(e){
    showToast('Verbindung zur App wird wiederhergestellt ...', 'error');
  }
}
setInterval(pull, 2000); pull();
setInterval(() => refreshRadar(true), 300000);

function openMenu(){
  const menu = byId('menu');
  const btn = byId('menuBtn');
  if(!menu){ return; }
  menu.classList.remove('hidden');
  if(btn){ btn.setAttribute('aria-expanded', 'true'); }
  loadConfig().then(() => {
    const first = byId('cfgStream');
    if(first){ first.focus(); }
  });
}

function closeMenu(){
  const menu = byId('menu');
  const btn = byId('menuBtn');
  if(!menu){ return; }
  menu.classList.add('hidden');
  if(btn){ btn.setAttribute('aria-expanded', 'false'); btn.focus(); }
}

function fillForm(cfg){
  currentConfig = cfg;
  byId('cfgStream').value = (cfg.stream && cfg.stream.url) || '';
  byId('cfgLabel').value = (cfg.location && cfg.location.label) || 'Bielefeld';
  byId('cfgLat').value = (cfg.location && cfg.location.latitude) || 52.0302;
  byId('cfgLon').value = (cfg.location && cfg.location.longitude) || 8.5325;
  byId('cfgLayout').value = (cfg.ui && cfg.ui.layout_profile) || 'auto';
  byId('cfgRadarH').value = (cfg.ui && cfg.ui.radar && cfg.ui.radar.height) || 180;
  byId('showWeather').checked = !!(cfg.ui && cfg.ui.weather && cfg.ui.weather.enabled);
  byId('showRadar').checked = !!(cfg.ui && cfg.ui.radar && cfg.ui.radar.enabled);
  byId('showTransit').checked = !!(cfg.ui && cfg.ui.transit && cfg.ui.transit.enabled);
  byId('showSystem').checked = !!(cfg.ui && cfg.ui.system && cfg.ui.system.enabled);
  byId('cfgStops').value = JSON.stringify((cfg.transit && cfg.transit.stops) || [], null, 2);
}

async function loadConfig(){
  const r = await fetch('/api/config?_=' + Date.now(), {cache:'no-store'});
  const d = await r.json();
  fillForm(d.config);
  setStatus('Config: ' + d.path);
}

function readForm(){
  const cfg = JSON.parse(JSON.stringify(currentConfig || {}));
  cfg.stream = cfg.stream || {};
  cfg.location = cfg.location || {};
  cfg.ui = cfg.ui || {};
  cfg.ui.weather = cfg.ui.weather || {};
  cfg.ui.radar = cfg.ui.radar || {};
  cfg.ui.transit = cfg.ui.transit || {};
  cfg.ui.system = cfg.ui.system || {};
  cfg.transit = cfg.transit || {};

  const stream = byId('cfgStream').value.trim();
  if(!stream){ throw new Error('Livestream URL fehlt.'); }

  cfg.stream.url = stream;
  cfg.location.label = byId('cfgLabel').value.trim() || 'Bielefeld';
  cfg.location.latitude = parseFloat(byId('cfgLat').value || '52.0302');
  cfg.location.longitude = parseFloat(byId('cfgLon').value || '8.5325');
  cfg.ui.layout_profile = byId('cfgLayout').value;
  cfg.ui.radar.height = Math.max(120, Math.min(420, parseInt(byId('cfgRadarH').value || '180', 10)));
  cfg.ui.weather.enabled = byId('showWeather').checked;
  cfg.ui.radar.enabled = byId('showRadar').checked;
  cfg.ui.transit.enabled = byId('showTransit').checked;
  cfg.ui.system.enabled = byId('showSystem').checked;

  try{
    cfg.transit.stops = JSON.parse(byId('cfgStops').value || '[]');
  }catch(e){
    throw new Error('Haltestellen JSON ist ungültig.');
  }

  return cfg;
}

function shortStopTitle(name){
  const cleaned = String(name || 'Haltestelle')
    .replace('Bielefeld', '')
    .replace('Bi-', '')
    .trim()
    .replace(/^,\s*/, '');
  return cleaned.split(',')[0].trim() || 'Haltestelle';
}

function stationToStop(station){
  return {
    title: shortStopTitle(station.station_name),
    station_name: station.station_name,
    station_id: station.station_id,
    line_filter: [],
    nightbus_only: false,
    hide_if_empty: true,
    max_rows: 3,
  };
}

function renderStationResults(results){
  const root = byId('stationResults');
  if(!root){ return; }
  root.replaceChildren();

  if(!results || !results.length){
    const empty = document.createElement('div');
    empty.className = 'station-empty';
    empty.textContent = 'Keine Haltestelle gefunden. Prüfe die Schreibweise oder suche allgemeiner.';
    root.appendChild(empty);
    return;
  }

  results.forEach(station => {
    const row = document.createElement('div');
    row.className = 'station-result';

    const text = document.createElement('div');
    const name = document.createElement('strong');
    name.textContent = station.station_name || 'Haltestelle';
    const meta = document.createElement('span');
    meta.textContent = station.station_id ? 'ID ' + station.station_id : 'VRR-Haltestelle';
    text.appendChild(name);
    text.appendChild(meta);

    const btn = document.createElement('button');
    btn.className = 'button button-primary';
    btn.type = 'button';
    btn.textContent = 'Übernehmen';
    btn.addEventListener('click', () => {
      const cfg = JSON.parse(JSON.stringify(currentConfig || {}));
      cfg.transit = cfg.transit || {};
      cfg.transit.stops = [stationToStop(station)];
      cfg.ui = cfg.ui || {};
      cfg.ui.transit = cfg.ui.transit || {};
      cfg.ui.transit.enabled = true;
      currentConfig = cfg;
      fillForm(cfg);
      setStatus('Haltestelle übernommen. Speichern nicht vergessen.', 'success');
      showToast('Haltestelle übernommen', 'success');
    });

    row.appendChild(text);
    row.appendChild(btn);
    root.appendChild(row);
  });
}

async function saveConfig(){
  try{
    const cfg = readForm();
    setStatus('Speichere ...');
    const r = await fetch('/api/config/save', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({config:cfg}),
    });
    const d = await r.json();
    if(d.ok){
      currentConfig = cfg;
      setStatus('Gespeichert: ' + d.path, 'success');
      showToast('Einstellungen gespeichert', 'success');
      lastRadarRefresh = 0;
      pull();
    }else{
      setStatus('Fehler: ' + (d.error || 'unbekannt'), 'error');
      showToast('Speichern fehlgeschlagen', 'error');
    }
  }catch(e){
    setStatus('Fehler: ' + e.message, 'error');
    showToast(e.message, 'error');
  }
}

async function searchStation(){
  const q = byId('stationQuery').value.trim();
  if(!q){
    renderStationResults([]);
    setStatus('Bitte Suchbegriff eingeben.', 'error');
    return;
  }

  const btn = byId('stationSearchBtn');
  if(btn){ btn.disabled = true; btn.textContent = 'Sucht ...'; }
  setStatus('Haltestelle wird gesucht ...');

  try{
    const r = await fetch('/api/station/search?q=' + encodeURIComponent(q));
    const d = await r.json();
    renderStationResults(d.results || []);
    setStatus((d.results || []).length ? 'Suchergebnis auswählen und übernehmen.' : 'Keine Haltestelle gefunden.', (d.results || []).length ? undefined : 'error');
  }catch(e){
    renderStationResults([]);
    setStatus('Suche fehlgeschlagen: ' + e.message, 'error');
    showToast('Haltestellensuche fehlgeschlagen', 'error');
  }finally{
    if(btn){ btn.disabled = false; btn.textContent = 'Suchen'; }
  }
}

byId('menuBtn').addEventListener('click', openMenu);
byId('closeMenu').addEventListener('click', closeMenu);
byId('saveConfig').addEventListener('click', saveConfig);
byId('reloadConfig').addEventListener('click', () => loadConfig().then(() => showToast('Config neu geladen', 'success')));
byId('stationSearchBtn').addEventListener('click', searchStation);
byId('settingsForm').addEventListener('submit', event => event.preventDefault());
byId('stationQuery').addEventListener('keydown', event => {
  if(event.key === 'Enter'){
    event.preventDefault();
    searchStation();
  }
});

document.addEventListener('keydown', event => {
  if(event.key === 'Escape' && !byId('menu').classList.contains('hidden')){
    closeMenu();
  }
});
