const signs=[
{id:"aries",name:"Aries",glyph:"♈",dates:"MAR 21 — APR 19",element:"FIRE · CARDINAL",theme:["#fc7c78","#ebc399","rgba(252,124,120,.22)","linear-gradient(140deg,#fc7c78 0%,#f5976c 42%,#ebc399 100%)"],layout:"solar"},
{id:"taurus",name:"Taurus",glyph:"♉",dates:"APR 20 — MAY 20",element:"EARTH · FIXED",theme:["#ea6171","#e19ba4","rgba(234,97,113,.20)","linear-gradient(60deg,#e19ba4 0%,#ec77a6 48%,#ea6171 100%)"],layout:"earth"},
{id:"gemini",name:"Gemini",glyph:"♊",dates:"MAY 21 — JUN 20",element:"AIR · MUTABLE",theme:["#8cbc72","#bac585","rgba(140,188,114,.20)","linear-gradient(60deg,#abc09d 0%,#bac585 48%,#8cbc72 100%)"],layout:"split"},
{id:"cancer",name:"Cancer",glyph:"♋",dates:"JUN 21 — JUL 22",element:"WATER · CARDINAL",theme:["#fb8971","#f0c55d","rgba(251,137,113,.20)","radial-gradient(circle at top right,#f0c55d 0%,#f39f79 55%,#fb8971 100%)"],layout:"lunar"},
{id:"leo",name:"Leo",glyph:"♌",dates:"JUL 23 — AUG 22",element:"FIRE · FIXED",theme:["#c5af66","#a0c050","rgba(197,175,102,.20)","linear-gradient(170deg,#a0c050 0%,#c2c261 50%,#c5af66 100%)"],layout:"solar"},
{id:"virgo",name:"Virgo",glyph:"♍",dates:"AUG 23 — SEP 22",element:"EARTH · MUTABLE",theme:["#f1848a","#efbeba","rgba(241,132,138,.20)","radial-gradient(circle at bottom left,#ef8878 0%,#f791a9 54%,#efbeba 100%)"],layout:"earth"},
{id:"libra",name:"Libra",glyph:"♎",dates:"SEP 23 — OCT 22",element:"AIR · CARDINAL",theme:["#a682ee","#c1acec","rgba(166,130,238,.22)","linear-gradient(70deg,#bba5ec 0%,#b3a8f5 55%,#a682ee 100%)"],layout:"split"},
{id:"scorpio",name:"Scorpio",glyph:"♏",dates:"OCT 23 — NOV 21",element:"WATER · FIXED",theme:["#d991fb","#eeb5e8","rgba(217,145,251,.22)","radial-gradient(circle at bottom left,#d991fb 0%,#f17ee2 58%,#eeb5e8 100%)"],layout:"lunar"},
{id:"sagittarius",name:"Sagittarius",glyph:"♐",dates:"NOV 22 — DEC 21",element:"FIRE · MUTABLE",theme:["#a693fa","#dbb5ee","rgba(166,147,250,.22)","linear-gradient(50deg,#a693fa 0%,#cb7af1 48%,#dbb5ee 100%)"],layout:"horizon"},
{id:"capricorn",name:"Capricorn",glyph:"♑",dates:"DEC 22 — JAN 19",element:"EARTH · CARDINAL",theme:["#6ccab0","#8cb4bf","rgba(108,202,176,.20)","linear-gradient(90deg,#8cb4bf 0%,#6ccab0 48%,#5eabc1 100%)"],layout:"earth"},
{id:"aquarius",name:"Aquarius",glyph:"♒",dates:"JAN 20 — FEB 18",element:"AIR · FIXED",theme:["#56dcde","#66b9d9","rgba(86,220,222,.20)","radial-gradient(circle at bottom left,#56dcde 0%,#58acd4 55%,#4f9bd5 100%)"],layout:"horizon"},
{id:"pisces",name:"Pisces",glyph:"♓",dates:"FEB 19 — MAR 20",element:"WATER · MUTABLE",theme:["#5f68cd","#66b9d9","rgba(95,104,205,.22)","radial-gradient(circle at bottom left,#5f68cd 0%,#5c8cd6 52%,#66b9d9 100%)"],layout:"lunar"}
];
function locationFromData(entry){
  const c=entry.conditions,r=entry.report;
  return {name:r.location,today:{conditions:c,horoscopes:Object.fromEntries(r.horoscopes.map(h=>[h.sign,h]))},future:entry.future};
}
const locations={bondi:locationFromData(window.SURF_DATA["Bondi Beach"]),byron:locationFromData(window.SURF_DATA["Byron Bay"])};
let activeLocation="bondi",activeSign="aries",activePeriod="today";
const signGrid=document.querySelector("#sign-grid");
signs.forEach((sign,i)=>{const button=document.createElement("button");button.className="sign-button";button.dataset.sign=sign.id;button.setAttribute("role","option");button.setAttribute("aria-selected",sign.id===activeSign);button.innerHTML=`<span class="glyph">${sign.glyph}</span><span class="name">${sign.name.toUpperCase()}</span>`;button.addEventListener("click",()=>{activeSign=sign.id;render()});signGrid.appendChild(button)});
document.querySelectorAll(".location-tab").forEach(button=>button.addEventListener("click",()=>{activeLocation=button.dataset.location;render()}));
document.querySelectorAll(".time-tab").forEach(button=>button.addEventListener("click",()=>{activePeriod=button.dataset.period;render()}));
signGrid.addEventListener("keydown",event=>{if(!["ArrowRight","ArrowLeft","ArrowDown","ArrowUp"].includes(event.key))return;event.preventDefault();const current=signs.findIndex(sign=>sign.id===activeSign);const step=event.key==="ArrowRight"?1:event.key==="ArrowLeft"?-1:event.key==="ArrowDown"?4:-4;activeSign=signs[(current+step+signs.length)%signs.length].id;render();document.querySelector(`[data-sign="${activeSign}"]`).focus()});
function setText(id,text){document.querySelector(`#${id}`).textContent=text}
function displayDate(value){return new Date(`${value}T00:00:00+10:00`).toLocaleDateString("en-AU",{weekday:"long",day:"numeric",month:"long"})}
function render(){
  const sign=signs.find(s=>s.id===activeSign),location=locations[activeLocation],index=signs.indexOf(sign)+1;
  const future=location.future[sign.name],snapshot=activePeriod==="future"?future:{conditions:location.today.conditions,horoscope:location.today.horoscopes[sign.name],date:null};
  const c=snapshot.conditions,reading=snapshot.horoscope;
  document.documentElement.style.setProperty("--sign",sign.theme[0]);document.documentElement.style.setProperty("--sign-soft",sign.theme[1]);document.documentElement.style.setProperty("--glow",sign.theme[2]);document.documentElement.style.setProperty("--sign-gradient",sign.theme[3]);document.body.dataset.layout=sign.layout;document.body.dataset.period=activePeriod;
  document.querySelectorAll(".location-tab").forEach(b=>{const on=b.dataset.location===activeLocation,tabLocation=locations[b.dataset.location],tabSnapshot=activePeriod==="future"?tabLocation.future[sign.name].conditions:tabLocation.today.conditions;b.classList.toggle("active",on);b.setAttribute("aria-selected",on);b.querySelector(".tab-state").textContent=on?"Selected":"Select";b.querySelector(".tab-detail").textContent=`${Number(tabSnapshot.wave_height_m).toFixed(1)} m · ${tabSnapshot.wind_direction} wind`});
  document.querySelectorAll(".time-tab").forEach(b=>{const on=b.dataset.period===activePeriod;b.classList.toggle("active",on);b.setAttribute("aria-selected",on)});
  document.querySelectorAll(".sign-button").forEach(b=>{const on=b.dataset.sign===activeSign;b.classList.toggle("selected",on);b.setAttribute("aria-selected",on)});
  setText("sign-index",`${String(index).padStart(2,"0")} / 12`);setText("zodiac-glyph",sign.glyph);setText("element-label",sign.element);setText("location-label",activePeriod==="future"?`${displayDate(snapshot.date).toUpperCase()} · ${location.name.toUpperCase()}`:location.name.toUpperCase());setText("sign-dates",sign.dates);setText("reading-period-label",activePeriod==="future"?"YOUR FUTURE READING":"TODAY'S OCEAN READING");setText("reading-title",reading.headline);setText("mantra",reading.surf_intention);setText("reading-copy",reading.reading);setText("cosmic-context",reading.cosmic_alignment);setText("conditions-time",activePeriod==="future"?`THE OCEAN · ${displayDate(snapshot.date).toUpperCase()}`:"THE OCEAN, NOW");setText("conditions-location",location.name);setText("wave-height",Number(c.wave_height_m).toFixed(1));setText("wave-period",String(Math.round(c.primary_period_s)).padStart(2,"0"));setText("wind-direction",c.wind_direction);setText("wind-speed",`${Number(c.wind_speed_m_s).toFixed(1)} m/s · ${c.wind_quality}`);setText("conditions-note",c.ocean_feeling)
}
render();
