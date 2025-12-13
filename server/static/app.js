const api = {
  base: '',
  state: { gameId: null, ws: null, lastIndex: -1, snapshot: null, status: null, players: [], colors: ["#22d3ee","#f59e0b","#ef4444","#84cc16","#a78bfa","#f472b6","#10b981","#eab308"] },
};

const boardEl = document.getElementById('board');
const eventsEl = document.getElementById('events');
const statusEl = document.getElementById('status');
const gameIdEl = document.getElementById('game-id');
const pauseBtn = document.getElementById('pause-btn');
const resumeBtn = document.getElementById('resume-btn');
const tickMsInput = document.getElementById('tick-ms');
const speedRange = document.getElementById('speed-range');
const feedSearch = document.getElementById('feed-search');
const turnSlider = document.getElementById('turn-slider');
const turnMeta = document.getElementById('turns-meta');
const turnEventsEl = document.getElementById('turn-events');
const playersEl = document.getElementById('players');

// Board names in standard order (0..39)
const boardNames = [
  'GO',
  'Mediterranean Avenue','Community Chest','Baltic Avenue','Income Tax','Reading Railroad',
  'Oriental Avenue','Chance','Vermont Avenue','Connecticut Avenue','Jail',
  'St. Charles Place','Electric Company','States Avenue','Virginia Avenue','Pennsylvania Railroad',
  'St. James Place','Community Chest','Tennessee Avenue','New York Avenue','Free Parking',
  'Kentucky Avenue','Chance','Indiana Avenue','Illinois Avenue','B. & O. Railroad',
  'Atlantic Avenue','Ventnor Avenue','Water Works','Marvin Gardens','Go To Jail',
  'Pacific Avenue','North Carolina Avenue','Community Chest','Pennsylvania Avenue','Short Line',
  'Chance','Park Place','Luxury Tax','Boardwalk'
];

// Board coordinates map for positions 0..39 (11x11 grid)
function positionToGrid(pos){
  const map = [];
  // bottom row 0..10
  for(let i=0;i<=10;i++){ map[i]=[10, i]; }
  // left column 11..20
  for(let i=1;i<=9;i++){ map[10+i]=[10-i, 10]; }
  map[20]=[0,10];
  // top row 21..30
  for(let i=1;i<=9;i++){ map[20+i]=[0, 10-i]; }
  map[30]=[0,0];
  // right column 31..39
  for(let i=1;i<=9;i++){ map[30+i]=[i,0]; }
  map[40]=map[0];
  return map[pos];
}

function renderBoard(snapshot){
  boardEl.innerHTML = '';
  api.state.posCells = {};
  // draw 11x11 grid, only border cells are visible as Monopoly board
  for(let r=0;r<11;r++){
    for(let c=0;c<11;c++){
      const cell = document.createElement('div');
      cell.className = 'cell';
      // find position that maps to this cell
      let label = '', num = '';
      for(let p=0;p<40;p++){
        const [rr,cc] = positionToGrid(p);
        if(rr===r && cc===c){
          num = String(p);
          label = boardNames[p] || '';
          if([0,10,20,30].includes(p)) cell.classList.add('corner');
          api.state.posCells[p] = cell;
          break;
        }
      }
      const numEl = document.createElement('div'); numEl.className = 'num'; numEl.textContent = num; cell.appendChild(numEl);
      const labelEl = document.createElement('div'); labelEl.className = 'label'; labelEl.textContent = label; cell.appendChild(labelEl);
      cell.style.gridRow = r+1;
      cell.style.gridColumn = c+1;
      boardEl.appendChild(cell);
    }
  }
}

function renderTokens(snapshot){
  const players = snapshot.players || [];
  // Clear previous tokens
  const cells = Array.from(boardEl.children);
  cells.forEach(cell=>{
    cell.querySelectorAll('.token').forEach(el=>el.remove());
  });
  players.forEach((p, idx)=>{
    const [r,c] = positionToGrid(p.position);
    const cell = cells[r*11 + c];
    const t = document.createElement('div');
    t.className = 'token';
    t.style.background = api.state.colors[idx % api.state.colors.length];
    t.title = `${p.name} (#${p.player_id})`;
    // Offset tokens to avoid full overlap
    const offset = (idx % 4);
    t.style.right = (2 + (offset%2)*14) + 'px';
    t.style.bottom = (14 + Math.floor(offset/2)*14) + 'px';
    cell.appendChild(t);
  });
}

function renderOwnership(snapshot){
  // reset outlines
  if(!api.state.posCells) return;
  Object.values(api.state.posCells).forEach(cell=>{ cell.style.boxShadow=''; cell.style.outline=''; });
  const players = snapshot.players || [];
  players.forEach((p, idx)=>{
    const color = api.state.colors[idx % api.state.colors.length];
    (p.properties||[]).forEach(prop=>{
      const cell = api.state.posCells[prop.position];
      if(cell){
        cell.style.boxShadow = `inset 0 0 0 3px ${color}`;
      }
    });
  });
}

function pidName(id){
  const ps = api.state.snapshot?.players || [];
  const p = ps.find(x=>x.player_id===id);
  return p ? p.name : `P${id}`;
}

function addEventLine(ev){
  const li = document.createElement('li');
  const type = ev.event_type;
  let txt = type;
  if(type==='dice_roll'){
    txt = `🎲 ${pidName(ev.player_id)}: ${ev.die1}+${ev.die2}=${ev.total}${ev.is_doubles?' (dbl)':''}`;
  } else if(type==='move'){
    txt = `🚶 ${pidName(ev.player_id)}: ${ev.from_position}→${ev.to_position} (${ev.space_name||''})`;
  } else if(type==='purchase'){
    txt = `💰 ${pidName(ev.player_id)} buys ${ev.property_name} for $${ev.price}`;
  } else if(type==='rent_payment'){
    txt = `💸 ${pidName(ev.payer_id)} → ${pidName(ev.owner_id)} $${ev.amount} (${ev.property_name||''})`;
  } else if(type==='auction_start'){
    txt = `🔨 Auction: ${ev.property_name}`;
  } else if(type==='auction_end'){
    txt = `🔨 Winner: ${pidName(ev.winner_id)} for $${ev.winning_bid}`;
  } else if(type==='turn_start'){
    txt = `▶️ Turn ${ev.turn_number} (${pidName(ev.player_id)})`;
  } else if(type==='go_to_jail'){
    txt = `🚔 ${pidName(ev.player_id)} to jail`;
  }
  li.textContent = txt;
  // With column-reverse in CSS, appending puts newest visually at the top
  eventsEl.appendChild(li);
  li.dataset.type = type;
  // Categories
  if(type.startsWith('auction')) li.dataset.cat = 'auction';
  else if(type.startsWith('card')) li.dataset.cat = 'card';
  else if(type.includes('rent')||type.includes('tax')||type.includes('payment')) li.dataset.cat = 'payment';
  else if(type==='move'||type==='dice_roll') li.dataset.cat = type;
  else li.dataset.cat = 'other';
  applyFeedFilters();
}

async function fetchStatus(){
  if(!api.state.gameId) return;
  const r = await fetch(`/games/${api.state.gameId}/status`);
  const s = await r.json();
  api.state.status = s;
  statusEl.textContent = JSON.stringify(s, null, 2);
  const enable = !!api.state.gameId;
  pauseBtn.disabled = !enable;
  resumeBtn.disabled = !enable;
  stepBtn.disabled = !enable;
}

// No actions in observer mode

function connectWS(){
  const url = `${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/games/${api.state.gameId}`;
  const ws = new WebSocket(url);
  api.state.ws = ws;
  ws.onmessage = (e)=>{
    const msg = JSON.parse(e.data);
    if(msg.type==='snapshot'){
      api.state.snapshot = msg.snapshot;
      api.state.lastIndex = msg.last_event_index ?? -1;
      // players legend
      playersEl.innerHTML = '';
      (api.state.snapshot.players||[]).forEach((p,idx)=>{
        const li = document.createElement('li');
        const dot = document.createElement('span'); dot.className='dot'; dot.style.background = api.state.colors[idx % api.state.colors.length];
        li.appendChild(dot);
        li.appendChild(document.createTextNode(` ${p.name} (#${p.player_id})`));
        playersEl.appendChild(li);
      });
      renderBoard(api.state.snapshot);
      renderTokens(api.state.snapshot);
      renderOwnership(api.state.snapshot);
      fetchStatus();
    } else if(msg.type==='events'){
      msg.events.forEach(ev=> addEventLine(ev));
      api.state.lastIndex = msg.to_index;
      // Update tokens on move/land/purchase etc.
      fetch(`/games/${api.state.gameId}/snapshot`).then(r=>r.json()).then(snap=>{
        api.state.snapshot = snap;
        renderTokens(snap);
        renderOwnership(snap);
        fetchStatus();
      });
    }
  };
  ws.onclose = ()=>{ setTimeout(connectWS, 1000); };
}

document.getElementById('create-form').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const players = parseInt(document.getElementById('players').value, 10);
  const rolesStr = document.getElementById('roles').value.trim();
  const roles = rolesStr ? rolesStr.split(',').map(s=>s.trim()) : null;
  const maxTurns = parseInt(document.getElementById('max-turns').value, 10);
  const r = await fetch('/games', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ players, roles, max_turns: maxTurns }) });
  const d = await r.json();
  api.state.gameId = d.game_id;
  gameIdEl.textContent = `Game: ${api.state.gameId}`;
  pauseBtn.disabled = false; resumeBtn.disabled = false;
  connectWS();
});

pauseBtn.onclick = async ()=>{
  if(!api.state.gameId) return;
  await fetch(`/games/${api.state.gameId}/pause`, { method: 'POST' });
  await fetchStatus();
};
resumeBtn.onclick = async ()=>{
  if(!api.state.gameId) return;
  await fetch(`/games/${api.state.gameId}/resume`, { method: 'POST' });
  await fetchStatus();
};
speedRange.oninput = async ()=>{
  if(!api.state.gameId) return;
  const v = parseInt(speedRange.value,10);
  await fetch(`/games/${api.state.gameId}/speed`, { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({ tick_ms: v })});
};

feedSearch.oninput = ()=> applyFeedFilters();

function applyFeedFilters(){
  const q = (feedSearch.value||'').toLowerCase();
  const checks = {}; document.querySelectorAll('.flt').forEach(cb=> checks[cb.dataset.type]=cb.checked);
  Array.from(eventsEl.children).forEach(li=>{
    const t = li.dataset.type||''; const cat = li.dataset.cat||''; const txt = li.textContent.toLowerCase();
    const on = (
      (checks[t] || (cat && checks[cat]) || (t!=='dice_roll'&&t!=='move'&&checks['other'])) &&
      (q==='' || txt.includes(q))
    );
    li.style.display = on ? '' : 'none';
  });
}

// Filters change
document.addEventListener('change', (e)=>{
  if(e.target && e.target.classList && e.target.classList.contains('flt')) applyFeedFilters();
});

async function loadTurns(){
  if(!api.state.gameId) return;
  const r = await fetch(`/games/${api.state.gameId}/turns`);
  const d = await r.json();
  const turns = d.turns || [];
  if(turns.length){
    turnSlider.min = String(turns[0].turn_number);
    turnSlider.max = String(turns[turns.length-1].turn_number);
    turnSlider.value = turnSlider.max;
    turnMeta.textContent = `Turns: ${turns[0].turn_number}..${turns[turns.length-1].turn_number}`;
  }
}

turnSlider.oninput = async ()=>{
  if(!api.state.gameId) return;
  const t = parseInt(turnSlider.value,10);
  const r = await fetch(`/games/${api.state.gameId}/turns/${t}`);
  const d = await r.json();
  const evs = d.events || [];
  turnEventsEl.textContent = evs.map(ev=> `${ev.event_type}: ${JSON.stringify(ev)}`).join('\n');
};

// Periodically refresh turns metadata while connected
setInterval(loadTurns, 3000);
