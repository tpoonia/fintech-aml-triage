"""Animated and 3D visual components for the investigator dashboard.

Each component is a self-contained HTML document rendered with ``st.iframe``.
Three.js (r158) and GSAP (3.12) are vendored under ``static/vendor`` and served
by Streamlit's static file serving, with a CDN fallback, so a page update does
not resend the libraries.

Design rules followed by every component:
- Visuals encode real alert data (no decorative-only noise).
- ``prefers-reduced-motion`` disables autoplay motion and count-ups.
- Rendering pauses when the component is off screen or the browser tab is hidden.
- If WebGL is unavailable, the overlay content still renders.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

TIER_ORDER = ["P1", "P2", "P3", "P4"]
TIER_COLORS = {"P1": "#ff4d6d", "P2": "#ff9f43", "P3": "#f7c948", "P4": "#2dd4bf"}
TIER_LABELS = {"P1": "Critical", "P2": "High", "P3": "Medium", "P4": "Low"}

_LIBS = {
    "three": ["app/static/vendor/three.min.js", "/app/static/vendor/three.min.js",
              "https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js"],
    "gsap": ["app/static/vendor/gsap.min.js", "/app/static/vendor/gsap.min.js",
             "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"],
}

_BASE_CSS = """
:root{--bg:#070b16;--panel:rgba(14,21,38,.72);--line:rgba(148,163,184,.16);--text:#e6edf7;
--muted:#8b9ab4;--accent:#38bdf8;--p1:#ff4d6d;--p2:#ff9f43;--p3:#f7c948;--p4:#2dd4bf}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent;color:var(--text);
font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overflow:hidden}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
"""

_LOADER_JS = """
function loadScript(srcs){return new Promise(function(resolve,reject){
  (function attempt(i){ if(i>=srcs.length){reject(new Error('load failed'));return;}
    var s=document.createElement('script'); s.src=srcs[i]; s.async=false;
    s.onload=function(){resolve();}; s.onerror=function(){s.remove();attempt(i+1);};
    document.head.appendChild(s);})(0);});}
var REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function hasWebGL(){try{var c=document.createElement('canvas');
  return !!(window.WebGLRenderingContext&&(c.getContext('webgl2')||c.getContext('webgl')));}catch(e){return false;}}
function fmt(n,d){return Number(n).toLocaleString(undefined,{minimumFractionDigits:d||0,maximumFractionDigits:d||0});}
function countUp(el){var end=parseFloat(el.dataset.value),d=parseInt(el.dataset.decimals||'0'),
  suf=el.dataset.suffix||'';
  if(REDUCED||!window.gsap){el.textContent=fmt(end,d)+suf;return;}
  var o={v:0};gsap.to(o,{v:end,duration:1.6,ease:'power3.out',delay:parseFloat(el.dataset.delay||'0'),
    onUpdate:function(){el.textContent=fmt(o.v,d)+suf;}});}
function runWhileVisible(root,tick){var visible=true,raf=0,last=performance.now();
  function loop(t){raf=requestAnimationFrame(loop);var dt=Math.min(0.05,(t-last)/1000);last=t;
    if(visible&&!document.hidden)tick(dt,t/1000);}
  if('IntersectionObserver' in window){new IntersectionObserver(function(e){visible=e[0].isIntersecting;},
    {threshold:0.01}).observe(root);}
  raf=requestAnimationFrame(loop);}
"""


def _libs_js(*names: str) -> str:
    chain = "Promise.resolve()"
    for name in names:
        chain += f".then(function(){{return loadScript({json.dumps(_LIBS[name])});}})"
    return chain


def _stable_hash(values: pd.Series, buckets: int) -> np.ndarray:
    codes = values.astype(str).map(lambda s: sum((i + 1) * ord(ch) for i, ch in enumerate(s)))
    return (codes.to_numpy() % buckets).astype(int)


def _sample(df: pd.DataFrame, limit: int, seed: int = 7) -> pd.DataFrame:
    """Keep every P1/P2 alert, then a seeded sample of the rest."""

    if len(df) <= limit:
        return df
    urgent = df[df["priority"].astype(str).isin(["P1", "P2"])]
    if len(urgent) >= limit:
        return urgent.nlargest(limit, "risk_score")
    rest = df.drop(urgent.index)
    return pd.concat([urgent, rest.sample(limit - len(urgent), random_state=seed)])


# ---------------------------------------------------------------------------
# 1. Alert galaxy hero
# ---------------------------------------------------------------------------

def galaxy_payload(df: pd.DataFrame, limit: int = 6000) -> dict:
    data = _sample(df, limit)
    score = pd.to_numeric(data["risk_score"], errors="coerce").fillna(0).to_numpy(float)
    lo, hi = float(np.nanmin(score)), float(np.nanmax(score))
    norm = (score - lo) / (hi - lo) if hi > lo else np.full_like(score, 0.5)
    rng = np.random.default_rng(42)
    radius = 0.45 + 6.2 * np.power(1.0 - norm, 1.35) + rng.normal(0, 0.12, len(data))
    arms = 4
    arm = _stable_hash(data["customer_id"], arms) if "customer_id" in data else rng.integers(0, arms, len(data))
    theta = arm * (2 * math.pi / arms) + radius * 0.82 + rng.normal(0, 0.32, len(data)) / (0.6 + radius * 0.25)
    x = radius * np.cos(theta)
    z = radius * np.sin(theta)
    y = rng.normal(0, 0.16, len(data)) * (0.35 + radius / 5.0)
    tier = data["priority"].astype(str).map({t: i for i, t in enumerate(TIER_ORDER)}).fillna(2).astype(int).to_numpy()
    flat = np.round(np.column_stack([x, y, z]), 3).ravel().tolist()
    return {"pos": flat, "tier": tier.tolist(), "shown": int(len(data))}


def galaxy_hero(payload: dict, kpis: list[dict], counts: dict, total: int, height: int = 470) -> str:
    kpi_html = "".join(
        f'<div class="kpi" style="--d:{i * 0.08:.2f}s"><div class="k-label">{k["label"]}</div>'
        f'<div class="k-value" data-value="{k["value"]}" data-decimals="{k.get("decimals", 0)}" '
        f'data-suffix="{k.get("suffix", "")}" data-delay="{0.35 + i * 0.08:.2f}">0</div>'
        f'<div class="k-note">{k.get("note", "")}</div></div>'
        for i, k in enumerate(kpis)
    )
    legend = "".join(
        f'<div class="lg"><span class="dot" style="background:{TIER_COLORS[t]};box-shadow:0 0 10px {TIER_COLORS[t]}"></span>'
        f'<b>{t}</b><span class="lg-l">{TIER_LABELS[t]}</span><span class="mono lg-n">{counts.get(t, 0):,}</span></div>'
        for t in TIER_ORDER
    )
    doc = """<!doctype html><html><head><meta charset="utf-8"><style>__CSS__
.wrap{position:relative;height:__H__px;border-radius:22px;overflow:hidden;
 background:radial-gradient(120% 90% at 70% 40%,#13204a 0%,#0a1024 45%,#060913 100%);
 border:1px solid var(--line)}
canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
.ov{position:absolute;inset:0;display:flex;justify-content:space-between;padding:26px 30px;pointer-events:none}
.left{max-width:640px;display:flex;flex-direction:column;justify-content:space-between}
.eyebrow{display:inline-flex;gap:8px;align-items:center;font-size:12px;letter-spacing:.14em;text-transform:uppercase;
 color:#9fd8ff;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.28);padding:6px 11px;border-radius:999px;width:max-content}
.live{width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 0 0 rgba(52,211,153,.6);animation:ping 2s infinite}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(52,211,153,.55)}70%{box-shadow:0 0 0 9px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}
h1{font-size:40px;line-height:1.05;margin:14px 0 8px;font-weight:800;letter-spacing:-.035em;
 background:linear-gradient(92deg,#fff 0%,#c7e6ff 55%,#7dd3fc 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:#a9b6cc;font-size:15px;max-width:520px;line-height:1.5}
.kpis{display:grid;grid-template-columns:repeat(__NK__,minmax(0,1fr));gap:10px;margin-top:18px}
.kpi{background:rgba(10,16,32,.55);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
 border:1px solid var(--line);border-radius:14px;padding:12px 14px;opacity:0;transform:translateY(12px);
 animation:rise .7s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:var(--d)}
@keyframes rise{to{opacity:1;transform:none}}
.k-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.k-value{font-size:26px;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums}
.k-note{font-size:11px;color:#71809b;margin-top:2px}
.right{display:flex;flex-direction:column;justify-content:flex-end;align-items:flex-end;gap:10px}
.legend{background:rgba(10,16,32,.55);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:14px;padding:12px 14px;min-width:210px}
.lg{display:flex;align-items:center;gap:8px;font-size:13px;padding:3px 0}
.dot{width:9px;height:9px;border-radius:50%}.lg-l{color:var(--muted)}.lg-n{margin-left:auto;color:#cbd5e1}
.cap{font-size:11px;color:#71809b;max-width:230px;text-align:right;line-height:1.4}
@media (max-width:820px){.right{display:none}h1{font-size:30px}.kpis{grid-template-columns:repeat(2,1fr)}}
@media (prefers-reduced-motion:reduce){.kpi{animation:none;opacity:1;transform:none}.live{animation:none}}
</style></head><body><div class="wrap" id="root"><canvas id="c" aria-hidden="true"></canvas>
<div class="ov"><div class="left"><div>
<div class="eyebrow"><span class="live"></span>Synthetic AML operations · __TOTAL__ alerts scored</div>
<h1>AML Alert Triage Engine</h1>
<div class="sub">Every speck is one alert. The closer it sits to the glowing core, the higher its risk score. Pulsing red alerts are P1 and go to the top of the queue.</div>
</div><div class="kpis">__KPIS__</div></div>
<div class="right"><div class="legend" role="list" aria-label="Priority tiers">__LEGEND__</div>
<div class="cap">Showing __SHOWN__ alerts (every P1 and P2 plus a sample). Decision support only: human review is required.</div></div></div></div>
<script>__LOADER__
var DATA=__DATA__;
document.querySelectorAll('.k-value').forEach(function(el){el.textContent='0';});
__LIBS__.then(function(){
  document.querySelectorAll('.k-value').forEach(countUp);
  if(!hasWebGL()||!window.THREE)return;
  var root=document.getElementById('root'),canvas=document.getElementById('c');
  var renderer=new THREE.WebGLRenderer({canvas:canvas,antialias:true,alpha:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  var scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(52,1,0.1,200);
  camera.position.set(0,8.5,21);
  var galaxy=new THREE.Group();scene.add(galaxy);
  var n=DATA.tier.length,pos=new Float32Array(DATA.pos),col=new Float32Array(n*3),size=new Float32Array(n),pulse=new Float32Array(n);
  var tc=[new THREE.Color('#ff4d6d'),new THREE.Color('#ff9f43'),new THREE.Color('#f7c948'),new THREE.Color('#2dd4bf')];
  var ts=[3.4,2.5,1.25,1.15];
  for(var i=0;i<n;i++){var t=DATA.tier[i],c=tc[t];
    var dim=t>=2?0.55:1.0;col[i*3]=c.r*dim;col[i*3+1]=c.g*dim;col[i*3+2]=c.b*dim;
    size[i]=ts[t]*(0.8+Math.random()*0.4);pulse[i]=t===0?1:0;}
  var g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('aColor',new THREE.BufferAttribute(col,3));
  g.setAttribute('aSize',new THREE.BufferAttribute(size,1));g.setAttribute('aPulse',new THREE.BufferAttribute(pulse,1));
  var mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    uniforms:{uTime:{value:0},uPR:{value:renderer.getPixelRatio()}},
    vertexShader:'attribute vec3 aColor;attribute float aSize;attribute float aPulse;uniform float uTime;uniform float uPR;'+
      'varying vec3 vC;varying float vA;void main(){vec4 mv=modelViewMatrix*vec4(position,1.0);'+
      'float p=aPulse>0.5?1.0+0.55*sin(uTime*2.6+position.x*3.0+position.z*2.0):1.0;'+
      'gl_PointSize=aSize*p*uPR*(26.0/-mv.z);gl_Position=projectionMatrix*mv;vC=aColor;vA=aPulse>0.5?1.0:0.8;}',
    fragmentShader:'varying vec3 vC;varying float vA;void main(){float d=length(gl_PointCoord-vec2(0.5));'+
      'float a=smoothstep(0.5,0.0,d);a=a*a;gl_FragColor=vec4(vC,a*vA);}'});
  galaxy.add(new THREE.Points(g,mat));
  // glowing core
  var cv=document.createElement('canvas');cv.width=cv.height=128;var cx=cv.getContext('2d');
  var gr=cx.createRadialGradient(64,64,0,64,64,64);gr.addColorStop(0,'rgba(255,240,245,1)');
  gr.addColorStop(0.18,'rgba(255,110,140,.85)');gr.addColorStop(0.5,'rgba(120,60,200,.25)');gr.addColorStop(1,'rgba(0,0,0,0)');
  cx.fillStyle=gr;cx.fillRect(0,0,128,128);
  var core=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(cv),blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));
  core.scale.set(3.6,3.6,1);galaxy.add(core);
  // distant star field
  var sn=1400,sp=new Float32Array(sn*3);for(var j=0;j<sn;j++){var r=40+Math.random()*40,a=Math.random()*Math.PI*2,b=Math.acos(2*Math.random()-1);
    sp[j*3]=r*Math.sin(b)*Math.cos(a);sp[j*3+1]=r*Math.cos(b);sp[j*3+2]=r*Math.sin(b)*Math.sin(a);}
  var sg=new THREE.BufferGeometry();sg.setAttribute('position',new THREE.BufferAttribute(sp,3));
  scene.add(new THREE.Points(sg,new THREE.PointsMaterial({color:0x6b7fa8,size:0.12,transparent:true,opacity:0.55,depthWrite:false})));
  galaxy.rotation.x=0.18;
  function resize(){var w=root.clientWidth,h=root.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);
    camera.aspect=w/h;camera.updateProjectionMatrix();
    // keep the galaxy on the right on wide screens so the copy stays readable
    galaxy.position.x=w>820?3.6:0;}
  resize();if('ResizeObserver' in window)new ResizeObserver(resize).observe(root);else window.addEventListener('resize',resize);
  var target={x:0,y:0};
  if(!REDUCED){root.addEventListener('pointermove',function(e){var r=root.getBoundingClientRect();
    target.x=((e.clientX-r.left)/r.width-0.5);target.y=((e.clientY-r.top)/r.height-0.5);});
    gsap.to(camera.position,{y:4.4,z:11.5,duration:2.6,ease:'power3.out'});}
  else{camera.position.set(0,4.4,11.5);}
  var look=new THREE.Vector3(0,0,0);
  runWhileVisible(root,function(dt,time){
    mat.uniforms.uTime.value=REDUCED?0:time;
    if(!REDUCED){galaxy.rotation.y+=dt*0.06;
      camera.position.x+=(target.x*2.2-camera.position.x)*0.04;}
    look.set(galaxy.position.x*0.55,target.y*-0.6,0);camera.lookAt(look);
    renderer.render(scene,camera);});
}).catch(function(){document.querySelectorAll('.k-value').forEach(function(el){el.textContent=fmt(parseFloat(el.dataset.value),parseInt(el.dataset.decimals||'0'))+(el.dataset.suffix||'');});});
</script></body></html>"""
    return (
        doc.replace("__CSS__", _BASE_CSS)
        .replace("__H__", str(height))
        .replace("__NK__", str(len(kpis)))
        .replace("__KPIS__", kpi_html)
        .replace("__LEGEND__", legend)
        .replace("__TOTAL__", f"{total:,}")
        .replace("__SHOWN__", f"{payload['shown']:,}")
        .replace("__LOADER__", _LOADER_JS)
        .replace("__LIBS__", _libs_js("three", "gsap"))
        .replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    )


# ---------------------------------------------------------------------------
# 2. Interactive 3D risk explorer
# ---------------------------------------------------------------------------

def explorer_payload(df: pd.DataFrame, bounds: dict, limit: int = 5000) -> dict:
    data = _sample(df, limit, seed=11)
    ml = pd.to_numeric(data.get("ml_probability"), errors="coerce").fillna(0).to_numpy(float)
    beh = pd.to_numeric(data.get("behavioral_risk"), errors="coerce").fillna(0).to_numpy(float)
    amt = np.log10(pd.to_numeric(data.get("transaction_amount"), errors="coerce").fillna(0).clip(lower=0).to_numpy(float) + 1)

    def scale(v, key):
        lo, hi = bounds[key]
        return np.round((np.clip((v - lo) / (hi - lo if hi > lo else 1), 0, 1) - 0.5) * 8, 3)

    types = data.get("alert_type", pd.Series("UNKNOWN", index=data.index)).fillna("UNKNOWN").astype(str)
    type_list = sorted(types.unique().tolist())
    type_idx = types.map({t: i for i, t in enumerate(type_list)}).to_numpy()
    tier = data["priority"].astype(str).map({t: i for i, t in enumerate(TIER_ORDER)}).fillna(2).astype(int).to_numpy()
    raw_amt = pd.to_numeric(data.get("transaction_amount"), errors="coerce").fillna(0).to_numpy(float)
    return {
        "pos": np.column_stack([scale(ml, "ml"), scale(beh, "beh"), scale(amt, "amt")]).ravel().tolist(),
        "tier": tier.tolist(),
        "id": data["alert_id"].astype(str).tolist(),
        "risk": np.round(pd.to_numeric(data["risk_score"], errors="coerce").fillna(0).to_numpy(float), 1).tolist(),
        "ml": np.round(ml, 3).tolist(),
        "beh": np.round(beh, 3).tolist(),
        "amt": np.round(raw_amt, 2).tolist(),
        "type": type_idx.tolist(),
        "types": type_list,
        "shown": int(len(data)),
        "total": int(len(df)),
    }


def explorer_bounds(df: pd.DataFrame) -> dict:
    def rng(series):
        s = pd.to_numeric(series, errors="coerce").dropna()
        return [float(s.quantile(0.005)), float(s.quantile(0.995))] if len(s) else [0.0, 1.0]

    amt = np.log10(pd.to_numeric(df.get("transaction_amount"), errors="coerce").fillna(0).clip(lower=0) + 1)
    return {"ml": rng(df.get("ml_probability")), "beh": rng(df.get("behavioral_risk")), "amt": rng(amt)}


def risk_explorer(payload: dict, height: int = 600) -> str:
    counts = {t: 0 for t in TIER_ORDER}
    for t in payload["tier"]:
        counts[TIER_ORDER[t]] += 1
    chips = "".join(
        f'<button class="chip on" data-tier="{i}" aria-pressed="true" style="--c:{TIER_COLORS[t]}">'
        f'<span class="dot"></span>{t} <span class="mono">{counts[t]:,}</span></button>'
        for i, t in enumerate(TIER_ORDER)
    )
    doc = """<!doctype html><html><head><meta charset="utf-8"><style>__CSS__
.wrap{position:relative;height:__H__px;border-radius:20px;overflow:hidden;border:1px solid var(--line);
 background:radial-gradient(100% 80% at 50% 30%,#101a35 0%,#070b16 70%)}
canvas{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab;touch-action:none}
canvas.drag{cursor:grabbing}
.top{position:absolute;left:16px;right:16px;top:14px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;pointer-events:none}
.chips{display:flex;gap:8px;flex-wrap:wrap;pointer-events:auto}
.chip{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);background:rgba(10,16,32,.7);color:var(--text);
 border-radius:999px;padding:6px 11px;font:600 12px/1 inherit;cursor:pointer;transition:opacity .2s,border-color .2s}
.chip .dot{width:8px;height:8px;border-radius:50%;background:var(--c);box-shadow:0 0 8px var(--c)}
.chip:not(.on){opacity:.4}.chip.on{border-color:color-mix(in srgb,var(--c) 55%,transparent)}
.chip:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.hint{font-size:12px;color:var(--muted);background:rgba(10,16,32,.6);border:1px solid var(--line);border-radius:10px;padding:6px 10px}
.btn{pointer-events:auto;border:1px solid var(--line);background:rgba(10,16,32,.7);color:var(--text);border-radius:10px;padding:6px 10px;font:600 12px inherit;cursor:pointer}
.axes{position:absolute;left:16px;bottom:14px;font-size:12px;color:var(--muted);background:rgba(10,16,32,.6);
 border:1px solid var(--line);border-radius:12px;padding:9px 12px;line-height:1.6}
.axes b{color:var(--text)}.ax{display:inline-block;width:18px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
.tip{position:absolute;pointer-events:none;min-width:220px;background:rgba(8,12,24,.92);border:1px solid rgba(148,163,184,.3);
 border-radius:12px;padding:11px 13px;font-size:12px;opacity:0;transform:translateY(4px);transition:opacity .12s,transform .12s;
 box-shadow:0 12px 30px rgba(0,0,0,.45)}
.tip.show{opacity:1;transform:none}.tip h4{margin:0 0 6px;font-size:14px;display:flex;justify-content:space-between;gap:10px}
.tip .row{display:flex;justify-content:space-between;gap:14px;color:var(--muted)}.tip .row span:last-child{color:var(--text)}
.badge{font-size:11px;padding:2px 8px;border-radius:999px;font-weight:700}
.foot{position:absolute;right:16px;bottom:14px;font-size:11px;color:#71809b}
.nogl{position:absolute;inset:0;display:none;align-items:center;justify-content:center;color:var(--muted)}
</style></head><body><div class="wrap" id="root"><canvas id="c" role="img" aria-label="3D scatter of alerts by ML probability, behavioral risk and transaction amount"></canvas>
<div class="top"><div class="chips" role="group" aria-label="Show or hide priority tiers">__CHIPS__</div>
<div style="display:flex;gap:8px;align-items:flex-start"><span class="hint">Drag to rotate · scroll to zoom · hover a point</span>
<button class="btn" id="reset">Reset view</button></div></div>
<div class="axes"><div><span class="ax" style="background:#38bdf8"></span><b>X</b> ML probability</div>
<div><span class="ax" style="background:#a78bfa"></span><b>Y</b> Behavioral risk</div>
<div><span class="ax" style="background:#34d399"></span><b>Z</b> Transaction amount (log)</div></div>
<div class="foot">__SHOWN__ of __TOTAL__ filtered alerts plotted · every P1/P2 included</div>
<div class="tip" id="tip"></div><div class="nogl" id="nogl">3D view needs WebGL, which this browser has turned off.</div></div>
<script>__LOADER__
var D=__DATA__;
__LIBS__.then(function(){
  var root=document.getElementById('root'),canvas=document.getElementById('c'),tip=document.getElementById('tip');
  if(!hasWebGL()){document.getElementById('nogl').style.display='flex';return;}
  var renderer=new THREE.WebGLRenderer({canvas:canvas,antialias:true,alpha:true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  var scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(45,1,0.1,200);
  var world=new THREE.Group();scene.add(world);
  // bounding box + floor grid
  var box=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(8,8,8)),
    new THREE.LineBasicMaterial({color:0x334155,transparent:true,opacity:.7}));world.add(box);
  var grid=new THREE.GridHelper(8,8,0x1e293b,0x1e293b);grid.position.y=-4;world.add(grid);
  function axis(color,from,to){var g=new THREE.BufferGeometry().setFromPoints([from,to]);
    world.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:color})));}
  var o=new THREE.Vector3(-4,-4,-4);
  axis(0x38bdf8,o,new THREE.Vector3(4,-4,-4));axis(0xa78bfa,o,new THREE.Vector3(-4,4,-4));axis(0x34d399,o,new THREE.Vector3(-4,-4,4));
  function label(text,color,p){var c=document.createElement('canvas');c.width=512;c.height=96;var x=c.getContext('2d');
    x.font='700 52px Inter,system-ui,sans-serif';x.fillStyle=color;x.textAlign='center';x.textBaseline='middle';x.fillText(text,256,48);
    var s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true,depthWrite:false}));
    s.scale.set(3.9,0.73,1);s.position.copy(p);world.add(s);}
  label('ML probability →','#7dd3fc',new THREE.Vector3(0,-4.6,-4.4));
  label('Behavioral risk →','#c4b5fd',new THREE.Vector3(-4.9,0,-4.2));
  label('Amount →','#6ee7b7',new THREE.Vector3(-4.4,-4.6,0.4));
  // points
  var n=D.tier.length,pos=new Float32Array(D.pos),col=new Float32Array(n*3),vis=new Float32Array(n),sz=new Float32Array(n);
  var tc=[new THREE.Color('#ff4d6d'),new THREE.Color('#ff9f43'),new THREE.Color('#f7c948'),new THREE.Color('#2dd4bf')];
  var ts=[2.6,2.1,1.35,1.35];
  for(var i=0;i<n;i++){var c=tc[D.tier[i]];col[i*3]=c.r;col[i*3+1]=c.g;col[i*3+2]=c.b;vis[i]=1;sz[i]=ts[D.tier[i]];}
  var g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));
  g.setAttribute('aColor',new THREE.BufferAttribute(col,3));g.setAttribute('aVis',new THREE.BufferAttribute(vis,1));
  g.setAttribute('aSize',new THREE.BufferAttribute(sz,1));
  var mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    uniforms:{uPR:{value:renderer.getPixelRatio()},uHover:{value:-1},uIntro:{value:REDUCED?1:0}},
    vertexShader:'attribute vec3 aColor;attribute float aVis;attribute float aSize;uniform float uPR;uniform float uHover;uniform float uIntro;'+
      'varying vec3 vC;varying float vA;void main(){vec3 p=position*uIntro;vec4 mv=modelViewMatrix*vec4(p,1.0);'+
      'float h=abs(float(gl_VertexID)-uHover)<0.5?2.4:1.0;gl_PointSize=aSize*h*uPR*(30.0/-mv.z)*aVis;'+
      'gl_Position=projectionMatrix*mv;vC=aColor;vA=aVis;}',
    fragmentShader:'varying vec3 vC;varying float vA;void main(){if(vA<0.5)discard;float d=length(gl_PointCoord-vec2(0.5));'+
      'float a=smoothstep(0.5,0.05,d);gl_FragColor=vec4(vC,a*0.9);}'});
  var pts=new THREE.Points(g,mat);world.add(pts);
  if(!REDUCED)gsap.to(mat.uniforms.uIntro,{value:1,duration:1.6,ease:'expo.out',delay:0.1});
  // camera orbit (spherical)
  var sph={theta:0.85,phi:1.05,r:17},goal={theta:0.85,phi:1.05,r:17},auto=!REDUCED,drag=null;
  function place(){camera.position.set(sph.r*Math.sin(sph.phi)*Math.sin(sph.theta),sph.r*Math.cos(sph.phi),sph.r*Math.sin(sph.phi)*Math.cos(sph.theta));camera.lookAt(0,0,0);}
  canvas.addEventListener('pointerdown',function(e){drag={x:e.clientX,y:e.clientY};auto=false;canvas.classList.add('drag');canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointerup',function(e){drag=null;canvas.classList.remove('drag');});
  canvas.addEventListener('wheel',function(e){e.preventDefault();auto=false;goal.r=Math.max(7,Math.min(32,goal.r*(1+e.deltaY*0.001)));},{passive:false});
  document.getElementById('reset').addEventListener('click',function(){goal.theta=0.85;goal.phi=1.05;goal.r=17;});
  // tier toggles
  var hidden=[false,false,false,false];
  document.querySelectorAll('.chip').forEach(function(b){b.addEventListener('click',function(){var t=+b.dataset.tier;hidden[t]=!hidden[t];
    b.classList.toggle('on',!hidden[t]);b.setAttribute('aria-pressed',String(!hidden[t]));
    for(var i=0;i<n;i++)if(D.tier[i]===t)vis[i]=hidden[t]?0:1;g.attributes.aVis.needsUpdate=true;});});
  // hover picking
  var ray=new THREE.Raycaster();ray.params.Points.threshold=0.14;var mouse=new THREE.Vector2(),hoverPending=null;
  var names=['P1','P2','P3','P4'],colors=['#ff4d6d','#ff9f43','#f7c948','#2dd4bf'];
  canvas.addEventListener('pointermove',function(e){var r=root.getBoundingClientRect();
    if(drag){goal.theta-=(e.clientX-drag.x)*0.006;goal.phi=Math.max(0.2,Math.min(2.9,goal.phi-(e.clientY-drag.y)*0.006));drag={x:e.clientX,y:e.clientY};return;}
    hoverPending={x:e.clientX-r.left,y:e.clientY-r.top,w:r.width,h:r.height};});
  canvas.addEventListener('pointerleave',function(){tip.classList.remove('show');mat.uniforms.uHover.value=-1;hoverPending=null;});
  function pick(){if(!hoverPending)return;var p=hoverPending;hoverPending=null;
    mouse.set(p.x/p.w*2-1,-(p.y/p.h)*2+1);ray.setFromCamera(mouse,camera);
    var hits=ray.intersectObject(pts).filter(function(h){return vis[h.index]>0.5;});
    if(!hits.length){tip.classList.remove('show');mat.uniforms.uHover.value=-1;return;}
    var i=hits[0].index,t=D.tier[i];mat.uniforms.uHover.value=i;
    tip.innerHTML='<h4><span class="mono">'+D.id[i]+'</span><span class="badge" style="background:'+colors[t]+'22;color:'+colors[t]+'">'+names[t]+'</span></h4>'+
      '<div class="row"><span>Risk score</span><span class="mono">'+D.risk[i]+'</span></div>'+
      '<div class="row"><span>ML probability</span><span class="mono">'+(D.ml[i]*100).toFixed(1)+'%</span></div>'+
      '<div class="row"><span>Behavioral risk</span><span class="mono">'+D.beh[i].toFixed(2)+'</span></div>'+
      '<div class="row"><span>Amount</span><span class="mono">$'+fmt(D.amt[i],2)+'</span></div>'+
      '<div class="row"><span>Type</span><span>'+D.types[D.type[i]].replace(/_/g,' ').toLowerCase()+'</span></div>';
    var x=Math.min(p.x+16,p.w-240),y=Math.min(p.y+16,p.h-150);tip.style.left=x+'px';tip.style.top=y+'px';tip.classList.add('show');}
  function resize(){var w=root.clientWidth,h=root.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
  resize();if('ResizeObserver' in window)new ResizeObserver(resize).observe(root);
  runWhileVisible(root,function(dt){if(auto)goal.theta+=dt*0.12;
    sph.theta+=(goal.theta-sph.theta)*0.12;sph.phi+=(goal.phi-sph.phi)*0.12;sph.r+=(goal.r-sph.r)*0.12;
    place();pick();renderer.render(scene,camera);});
});
</script></body></html>"""
    return (
        doc.replace("__CSS__", _BASE_CSS)
        .replace("__H__", str(height))
        .replace("__CHIPS__", chips)
        .replace("__SHOWN__", f"{payload['shown']:,}")
        .replace("__TOTAL__", f"{payload['total']:,}")
        .replace("__LOADER__", _LOADER_JS)
        .replace("__LIBS__", _libs_js("three", "gsap"))
        .replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    )


# ---------------------------------------------------------------------------
# 3. Animated risk gauge + signal bars (Investigation Desk)
# ---------------------------------------------------------------------------

def risk_gauge(alert_id: str, score: float, tier: str, thresholds: dict, signals: list[tuple[str, float, str]],
               height: int = 270) -> str:
    """SVG gauge with tier bands from the shared thresholds; GSAP animates needle and bars."""

    import html as _html

    t_med, t_high, t_crit = thresholds["MEDIUM"], thresholds["HIGH"], thresholds["CRITICAL"]

    def arc(a0, a1, color):
        # angles in score units (0..100) mapped to 180..0 degrees
        def pt(v, r=100):
            ang = math.pi * (1 - v / 100)
            return 120 + r * math.cos(ang), 120 - r * math.sin(ang)
        x0, y0 = pt(a0)
        x1, y1 = pt(a1)
        return (f'<path d="M{x0:.2f},{y0:.2f} A100,100 0 0 1 {x1:.2f},{y1:.2f}" stroke="{color}" '
                f'stroke-width="16" fill="none" stroke-linecap="butt" opacity=".9"/>')

    bands = (arc(0, t_med - 0.6, TIER_COLORS["P4"]) + arc(t_med, t_high - 0.6, TIER_COLORS["P3"])
             + arc(t_high, t_crit - 0.6, TIER_COLORS["P2"]) + arc(t_crit, 100, TIER_COLORS["P1"]))
    color = TIER_COLORS.get(tier, "#94a3b8")
    bars = "".join(
        f'<div class="sig"><div class="sl"><span>{_html.escape(label)}</span><span class="mono">{_html.escape(text)}</span></div>'
        f'<div class="track"><div class="fill" data-w="{max(0.0, min(100.0, value)):.1f}"></div></div></div>'
        for label, value, text in signals
    )
    doc = """<!doctype html><html><head><meta charset="utf-8"><style>__CSS__
.wrap{display:grid;grid-template-columns:300px 1fr;gap:22px;align-items:center;height:__H__px;padding:18px 22px;
 border-radius:20px;border:1px solid var(--line);background:linear-gradient(140deg,#0e1730 0%,#0a1020 100%)}
.g{position:relative;text-align:center}.num{font-size:40px;font-weight:800;letter-spacing:-.03em;margin-top:2px;line-height:1;font-variant-numeric:tabular-nums}
.lbl{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em}
.tier{display:inline-block;margin-top:8px;padding:4px 12px;border-radius:999px;font-weight:700;font-size:12px;
 color:__C__;background:color-mix(in srgb,__C__ 16%,transparent);border:1px solid color-mix(in srgb,__C__ 45%,transparent)}
.sigs{display:grid;grid-template-columns:1fr 1fr;gap:12px 22px}
.sl{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:6px}.sl .mono{color:var(--text)}
.track{height:8px;border-radius:999px;background:rgba(148,163,184,.12);overflow:hidden}
.fill{height:100%;width:0;border-radius:999px;background:linear-gradient(90deg,#38bdf8,#a78bfa 60%,#ff4d6d)}
@media (max-width:760px){.wrap{grid-template-columns:1fr;height:auto}.sigs{grid-template-columns:1fr}}
</style></head><body><div class="wrap" id="root">
<div class="g" role="img" aria-label="Risk score __SCORE__ out of 100, tier __TIER__">
<svg viewBox="0 0 240 132" width="280"><defs><filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="240" height="132"><feGaussianBlur stdDeviation="2.5" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<path d="M20,120 A100,100 0 0 1 220,120" stroke="rgba(148,163,184,.12)" stroke-width="16" fill="none"/>__BANDS__
<g id="needle" transform="rotate(-90 120 120)" filter="url(#glow)">
<line x1="120" y1="120" x2="120" y2="32" stroke="__C__" stroke-width="3.5" stroke-linecap="round"/></g>
<circle cx="120" cy="120" r="8" fill="#0a1020" stroke="__C__" stroke-width="3"/></svg>
<div class="num" id="num" data-value="__SCORE__" data-decimals="0">0</div>
<div class="lbl">Risk score · __ID__</div><div class="tier">__TIER__ priority</div></div>
<div class="sigs">__BARS__</div></div>
<script>__LOADER__
var score=__SCORE__;
function finish(){var deg=-90+180*Math.max(0,Math.min(100,score))/100,needle=document.getElementById('needle');
  if(REDUCED||!window.gsap){needle.setAttribute('transform','rotate('+deg+' 120 120)');
    document.querySelectorAll('.fill').forEach(function(f){f.style.width=f.dataset.w+'%';});
    document.getElementById('num').textContent=Math.round(score);return;}
  var o={a:-90};gsap.to(o,{a:deg,duration:1.5,ease:'elastic.out(1,0.55)',
    onUpdate:function(){needle.setAttribute('transform','rotate('+o.a.toFixed(2)+' 120 120)');}});
  countUp(document.getElementById('num'));
  gsap.to('.fill',{width:function(i,el){return el.dataset.w+'%';},duration:1.1,ease:'power3.out',stagger:0.07,delay:0.2});}
__LIBS__.then(finish).catch(function(){REDUCED=true;finish();});
</script></body></html>"""
    return (
        doc.replace("__CSS__", _BASE_CSS)
        .replace("__H__", str(height))
        .replace("__BANDS__", bands)
        .replace("__BARS__", bars)
        .replace("__C__", color)
        .replace("__SCORE__", f"{float(score):.1f}")
        .replace("__TIER__", _html.escape(tier))
        .replace("__ID__", _html.escape(alert_id))
        .replace("__LOADER__", _LOADER_JS)
        .replace("__LIBS__", _libs_js("gsap"))
    )


# ---------------------------------------------------------------------------
# 4. Animated pipeline flow (Model & XAI)
# ---------------------------------------------------------------------------

def pipeline_flow(stages: list[tuple[str, str]], height: int = 130) -> str:
    import html as _html

    n = len(stages)
    w = 1100
    step = w / n
    nodes, links = [], []
    for i, (title, note) in enumerate(stages):
        cx = step * i + step / 2
        nodes.append(
            f'<g class="node" transform="translate({cx:.1f},70)"><rect x="-52" y="-28" width="104" height="56" rx="14"/>'
            f'<text y="-4" class="t">{_html.escape(title)}</text><text y="15" class="n">{_html.escape(note)}</text></g>'
        )
        if i < n - 1:
            links.append(f'<path class="link" d="M{cx + 56:.1f},70 L{cx + step - 56:.1f},70"/>')
    doc = """<!doctype html><html><head><meta charset="utf-8"><style>__CSS__
.wrap{height:__H__px;border-radius:20px;border:1px solid var(--line);background:linear-gradient(140deg,#0e1730,#0a1020);display:flex;align-items:center;justify-content:center;padding:10px}
svg{width:100%;height:auto;max-height:100%}
.node rect{fill:rgba(56,189,248,.07);stroke:rgba(56,189,248,.45);stroke-width:1.2}
.node .t{fill:#e6edf7;font:700 12.5px Inter,system-ui,sans-serif;text-anchor:middle}
.node .n{fill:#8b9ab4;font:500 10.5px Inter,system-ui,sans-serif;text-anchor:middle}
.link{stroke:#38bdf8;stroke-width:2;fill:none;stroke-dasharray:5 7;animation:flow 1.1s linear infinite;opacity:.8}
@keyframes flow{to{stroke-dashoffset:-24}}
@media (prefers-reduced-motion:reduce){.link{animation:none}}
</style></head><body><div class="wrap"><svg viewBox="0 30 1100 80" role="img" aria-label="Pipeline stages">__LINKS____NODES__</svg></div>
<script>__LOADER__
__LIBS__.then(function(){if(REDUCED)return;gsap.from('.node',{opacity:0,y:14,duration:.6,ease:'power2.out',stagger:.09});
  gsap.from('.link',{opacity:0,duration:.5,stagger:.09,delay:.3});}).catch(function(){});
</script></body></html>"""
    return (
        doc.replace("__CSS__", _BASE_CSS)
        .replace("__H__", str(height))
        .replace("__LINKS__", "".join(links))
        .replace("__NODES__", "".join(nodes))
        .replace("__LOADER__", _LOADER_JS)
        .replace("__LIBS__", _libs_js("gsap"))
    )
