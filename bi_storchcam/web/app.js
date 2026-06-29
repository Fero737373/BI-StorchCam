let currentConfig = null;

function byId(id){ return document.getElementById(id); }
function setText(id, text){ const el = byId(id); if(el) el.textContent = text; }

function tick(){
  const d = new Date();
  setText('clock', d.toLocaleTimeString('de-DE', {hour:'2-digit', minute:'2-digit', second:'2-digit'}));
}
setInterval(tick, 1000); tick();

function makeCell(text, cls){
  const td = document.createElement('td');
  td.textContent = text;
  if(cls) td.className = cls;
  return td;
}

function renderBoards(boards){
  const root = byId('boards');
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
    ['Linie','Ziel','Zeit'].forEach((x,i) => { const th=document.createElement('th'); th.textContent=x; if(i===2) th.className='time'; hr.appendChild(th); });
    head.appendChild(hr); table.appendChild(head);
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
      tr.appendChild(td); body.appendChild(tr);
    }
    table.appendChild(body); card.appendChild(table); root.appendChild(card);
  });
}

function applyUi(cfg){
  const ui = (cfg && cfg.ui) || {};
  document.body.classList.toggle('hide-weather', !(ui.weather && ui.weather.enabled));
  document.body.classList.toggle('hide-radar', !(ui.radar && ui.radar.enabled));
  document.body.classList.toggle('hide-transit', !(ui.transit && ui.transit.enabled));
  document.body.classList.toggle('hide-system', !(ui.system && ui.system.enabled));
  if(ui.radar && ui.radar.height){ byId('radar').style.height = ui.radar.height + 'px'; }
}

async function pull(){
  try{
    const r = await fetch('/api/state?_=' + Date.now(), {cache:'no-store'});
    const d = await r.json();
    const cfg = d.config || {};
    applyUi(cfg);
    const stream = (cfg.stream && cfg.stream.url) || '';
    if(stream && byId('live').src !== stream){ byId('live').src = stream; }
    const s = d.system || {};
    setText('sys', 'IP ' + (s.ip || '--') + ' | CPU ' + (s.cpu ?? '--') + '% | RAM ' + (s.ram ?? '--') + '% | Temp ' + (s.temp ?? '--') + '°C | Laufzeit ' + (s.uptime || '--'));
    const w = d.weather || {};
    setText('weatherText', w.text || 'Wetter lädt ...');
    renderBoards(d.boards || []);
  }catch(e){ }
}
setInterval(pull, 2000); pull();

function openMenu(){ byId('menu').classList.remove('hidden'); loadConfig(); }
function closeMenu(){ byId('menu').classList.add('hidden'); }
byId('menuBtn').addEventListener('click', openMenu);
byId('closeMenu').addEventListener('click', closeMenu);

function fillForm(cfg){
  currentConfig = cfg;
  byId('cfgStream').value = (cfg.stream && cfg.stream.url) || '';
  byId('cfgLabel').value = (cfg.location && cfg.location.label) || 'Bielefeld';
  byId('cfgLat').value = (cfg.location && cfg.location.latitude) || 52.0302;
  byId('cfgLon').value = (cfg.location && cfg.location.longitude) || 8.5325;
  byId('cfgLayout').value = (cfg.ui && cfg.ui.layout_profile) || 'auto';
  byId('cfgRadarH').value = (cfg.ui && cfg.ui.radar && cfg.ui.radar.height) || 190;
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
  setText('saveState', 'Config: ' + d.path);
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

  cfg.stream.url = byId('cfgStream').value.trim();
  cfg.location.label = byId('cfgLabel').value.trim() || 'Bielefeld';
  cfg.location.latitude = parseFloat(byId('cfgLat').value || '52.0302');
  cfg.location.longitude = parseFloat(byId('cfgLon').value || '8.5325');
  cfg.ui.layout_profile = byId('cfgLayout').value;
  cfg.ui.radar.height = parseInt(byId('cfgRadarH').value || '190', 10);
  cfg.ui.weather.enabled = byId('showWeather').checked;
  cfg.ui.radar.enabled = byId('showRadar').checked;
  cfg.ui.transit.enabled = byId('showTransit').checked;
  cfg.ui.system.enabled = byId('showSystem').checked;
  cfg.transit.stops = JSON.parse(byId('cfgStops').value || '[]');
  return cfg;
}

byId('saveConfig').addEventListener('click', async () => {
  try{
    const cfg = readForm();
    const r = await fetch('/api/config/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({config:cfg})});
    const d = await r.json();
    if(d.ok){ currentConfig = cfg; setText('saveState', 'Gespeichert: ' + d.path); closeMenu(); pull(); }
    else{ setText('saveState', 'Fehler: ' + (d.error || 'unbekannt')); }
  }catch(e){ setText('saveState', 'Fehler: ' + e.message); }
});
byId('reloadConfig').addEventListener('click', loadConfig);

byId('stationSearchBtn').addEventListener('click', async () => {
  const q = byId('stationQuery').value.trim();
  const r = await fetch('/api/station/search?q=' + encodeURIComponent(q));
  const d = await r.json();
  byId('stationResults').textContent = JSON.stringify(d.results || [], null, 2);
});
