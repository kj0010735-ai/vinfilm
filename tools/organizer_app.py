#!/usr/bin/env python3
"""프로젝트 정리 앱 — 내 컴퓨터에서만 도는 작은 서버 + 브라우저 화면 (VINFILM STUDIO)

앱을 실행하면 127.0.0.1의 임의 포트로 서버를 띄우고 화면을 연다 (Chrome 계열이 있으면 주소창 없는 전용 창).
창(탭)을 닫거나 화면의 '종료'를 누르면 서버도 같이 꺼진다. 외부에서는 접근할 수 없고
(로컬 주소 + 실행할 때마다 바뀌는 토큰), 표준 라이브러리만 쓴다.
"""
import json
import os
import secrets
import subprocess
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import organize_project as eng

STATE_PATH = eng.SUPPORT_DIR / "server.json"
TOKEN = secrets.token_urlsafe(16)
IDLE_LIMIT = 600   # 요청이 이 초 이상 없으면 종료
BYE_GRACE = 6      # 탭이 닫힌 뒤 새로고침 여부를 기다리는 시간

state = {"last": time.time(), "bye_at": None, "port": 0}


def folder_error(root):
    if not root.is_dir():
        return "폴더를 찾을 수 없어요."
    if root == Path.home() or len(root.parts) <= 3:
        return "너무 상위 폴더예요. 프로젝트 폴더를 직접 선택해 주세요."
    return None


def describe(root, cfg):
    moves, skipped, conflicts = eng.plan(root, cfg)
    groups = []
    for folder in eng.folder_names(cfg):
        items = [{"name": s.name, "dir": s.is_dir()} for s, d in moves if d.parent.name == folder]
        if items:
            groups.append({"folder": folder, "items": items})
    return {
        "total": len(moves),
        "groups": groups,
        "skipped": [{"name": s.name, "dir": s.is_dir()} for s in skipped],
        "conflicts": [{"name": s.name, "dir": s.is_dir()} for s, _ in conflicts],
        "hasUndo": eng.has_undo(root),
    }


def pick_folder():
    script = ('tell application "System Events"\n activate\n'
              ' set p to POSIX path of (choose folder with prompt "정리할 프리미어 프로젝트 폴더를 선택하세요")\n'
              'end tell\nreturn p')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def handle(path, body):
    if path == "config":
        return eng.load_config() if body is None else eng.save_config(body)
    if path == "config/reset":
        return eng.save_config(eng.DEFAULT_CONFIG)
    if path == "pick":
        return {"path": pick_folder()}
    if path in ("plan", "run", "undo"):
        root = Path(body.get("folder", "")).expanduser().resolve()
        err = folder_error(root)
        if err:
            return {"error": err}
        cfg = eng.normalize(body.get("config") or eng.load_config())
        if path == "plan":
            return describe(root, cfg)
        if path == "run":
            moves, _, _ = eng.plan(root, cfg)
            n, failed = eng.execute(root, moves, cfg, copy_mode=body.get("mode") == "copy")
            return {"done": n, "failed": failed}
        try:
            return {"undone": eng.undo(root)}
        except ValueError as e:
            return {"error": str(e)}
    return {"error": "알 수 없는 요청"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _reply(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self, query):
        # DNS rebinding 방지(Host 검사) + 토큰 검사
        host_ok = self.headers.get("Host", "") in (f"127.0.0.1:{state['port']}", f"localhost:{state['port']}")
        return host_ok and query.get("t", [""])[0] == TOKEN

    def _route(self, method):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if not self._authorized(query):
            return self._reply(403, "forbidden", "text/plain")
        state["last"], state["bye_at"] = time.time(), None
        if method == "GET" and url.path == "/":
            return self._reply(200, HTML.replace("__TOKEN__", TOKEN), "text/html; charset=utf-8")
        if not url.path.startswith("/api/"):
            return self._reply(404, "not found", "text/plain")
        api = url.path[5:]
        if api == "ping":
            return self._reply(200, "{}")
        if api == "bye":
            state["bye_at"] = time.time() + BYE_GRACE
            return self._reply(200, "{}")
        if api == "quit":
            self._reply(200, "{}")
            threading.Thread(target=shutdown, daemon=True).start()
            return
        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else {}
        try:
            result = handle(api, body)
        except Exception as e:  # 화면에 메시지로 보여주기 위해
            result = {"error": f"{type(e).__name__}: {e}"}
        self._reply(200, json.dumps(result, ensure_ascii=False))

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")


def shutdown():
    time.sleep(0.3)
    try:
        STATE_PATH.unlink()
    except OSError:
        pass
    os._exit(0)


def watchdog():
    while True:
        time.sleep(1)
        now = time.time()
        if state["bye_at"] and now > state["bye_at"]:
            shutdown()
        if now - state["last"] > IDLE_LIMIT:
            shutdown()


CHROMIUM_APPS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def open_ui(url):
    """Chrome 계열이 있으면 주소창 없는 전용 창(--app)으로, 없으면 기본 브라우저 탭으로 연다."""
    for exe in CHROMIUM_APPS:
        if os.path.exists(exe):
            subprocess.Popen([exe, f"--app={url}", "--window-size=960,860"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    webbrowser.open(url)


def already_running():
    """이미 떠 있는 인스턴스가 있으면 그 주소를 돌려준다."""
    try:
        s = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        url = f"http://127.0.0.1:{s['port']}/api/ping?t={s['token']}"
        urllib.request.urlopen(url, timeout=1).read()
        return f"http://127.0.0.1:{s['port']}/?t={s['token']}"
    except Exception:
        return None


def main():
    existing = already_running()
    if existing:
        open_ui(existing)
        return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state["port"] = server.server_address[1]
    eng.SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"port": state["port"], "token": TOKEN}), encoding="utf-8")
    url = f"http://127.0.0.1:{state['port']}/?t={TOKEN}"
    threading.Thread(target=watchdog, daemon=True).start()
    if os.environ.get("ORGANIZER_NO_BROWSER"):
        print(url, flush=True)
    else:
        open_ui(url)
    server.serve_forever()


HTML = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VINFILM 프로젝트 정리</title>
<style>
:root{--bg:#0e0d0c;--panel:#171513;--panel2:#1e1b18;--line:#2c2823;--text:#eee8e0;--dim:#9a9086;
--accent:#d98a3d;--accent-soft:rgba(217,138,61,.14);--bad:#d9634a;--ok:#8fbf77;
--font:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;
--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 var(--font)}
.wrap{max-width:820px;margin:0 auto;padding:36px 20px 80px}
.eyebrow{font:600 11px var(--mono);letter-spacing:.18em;color:var(--accent)}
h1{margin:4px 0 18px;font-size:26px;letter-spacing:-.01em}
.top{display:flex;justify-content:space-between;align-items:flex-start}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:22px}
.tab{background:none;border:0;color:var(--dim);font:inherit;font-weight:600;padding:9px 14px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.on{color:var(--text);border-color:var(--accent)}
.pane{display:none}.pane.on{display:block}
.btn{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#1a1108}
.btn.primary:hover{filter:brightness(1.08)}
.btn.ghost{background:none;color:var(--dim)}
.btn{white-space:nowrap;flex:none}
.btn:disabled{opacity:.4;cursor:default;filter:none}
.bar{display:flex;gap:12px;align-items:center;margin-bottom:16px}
.path{font:12px var(--mono);color:var(--dim);overflow-wrap:anywhere}
.sum{margin:18px 0 10px;font-weight:600}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:8px}
summary{cursor:pointer;padding:10px 14px;font-weight:600;list-style:none;display:flex;justify-content:space-between}
summary::-webkit-details-marker{display:none}
summary .n{color:var(--accent);font-family:var(--mono)}
details ul{margin:0;padding:0 14px 12px 30px;color:var(--dim);font-size:13px}
.warn{color:var(--bad)}
.note{margin:18px 0;padding:11px 14px;border-radius:8px;background:var(--accent-soft);color:var(--dim);font-size:13px}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}
.msg{margin-top:14px;min-height:20px;font-weight:600}
.msg.ok{color:var(--ok)}.msg.err{color:var(--bad)}
.empty{color:var(--dim);padding:24px 0}
.help{color:var(--dim);font-size:13px;margin:0 0 18px;padding-left:18px}
.help li{margin-bottom:4px}
.cat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:10px}
.cat-head{display:flex;gap:8px;align-items:center;margin-bottom:10px}
.num{font:600 12px var(--mono);color:var(--accent);width:22px}
.cat label{display:block;font-size:12px;color:var(--dim);margin-top:8px}
input[type=text]{width:100%;margin-top:4px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 10px;font:13px var(--font)}
input[type=text]:focus{outline:none;border-color:var(--accent)}
.fname{font:600 14px var(--mono)!important;margin-top:0!important}
.cat .chk{display:flex;gap:8px;align-items:center;color:var(--text);margin-top:10px}
.mini{background:var(--panel2);border:1px solid var(--line);color:var(--dim);border-radius:6px;width:30px;height:30px;cursor:pointer;flex:none}
.mini:hover{color:var(--text);border-color:var(--accent)}
.row2{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
.fb{margin-top:20px;padding:14px;background:var(--panel);border:1px solid var(--line);border-radius:10px}
.fb label{font-size:12px;color:var(--dim)}
.saved{font-size:12px;color:var(--dim);margin-left:8px}
</style></head><body><div class="wrap">
<div class="top"><div><div class="eyebrow">VINFILM STUDIO</div><h1>프로젝트 정리</h1></div>
<button class="btn ghost" data-act="quit">종료</button></div>
<div class="tabs"><button class="tab on" data-tab="run">정리</button><button class="tab" data-tab="set">분류 설정</button></div>
<div class="pane on" id="pane-run"></div>
<div class="pane" id="pane-set"></div>
</div>
<script>
const T="__TOKEN__";
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){
  const r=await fetch('/api/'+path+'?t='+T,{method:body===undefined?'GET':'POST',
    headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  return r.json();
}
let cfg=null,folder=null,plan=null,busy=false,msg={t:'',k:''};

const li=a=>a.map(i=>`<li>${esc(i.name)}${i.dir?'/':''}</li>`).join('');
function group(title,items,cls){
  return `<details ${items.length<=6?'open':''}><summary><span class="${cls||''}">${esc(title)}</span><span class="n">${items.length}</span></summary><ul>${li(items)}</ul></details>`;
}
function renderRun(){
  let h=`<div class="bar"><button class="btn" data-act="pick" ${busy?'disabled':''}>폴더 선택…</button>
    <span class="path">${folder?esc(folder):'정리할 프로젝트 폴더를 선택하세요'}</span></div>`;
  if(plan){
    if(plan.total===0) h+=`<div class="empty">정리할 항목이 없어요.</div>`;
    else{
      h+=`<div class="sum">총 ${plan.total}개 항목을 정리합니다</div>`;
      h+=plan.groups.map(g=>group(g.folder,g.items)).join('');
    }
    if(plan.conflicts.length) h+=group('같은 이름이 이미 있어 건너뜀',plan.conflicts,'warn');
    if(plan.skipped.length) h+=group('분류 못 해서 그대로 둠',plan.skipped);
    if(plan.total>0){
      h+=`<div class="note">파일을 옮기면 기존 프리미어 프로젝트는 '미디어 오프라인'이 뜹니다. 정리 후 프로젝트를 열어 Link Media로 한 번 연결해 주세요.</div>`;
    }
    h+=`<div class="actions">`;
    if(plan.total>0) h+=`<button class="btn primary" data-act="run" data-mode="move" ${busy?'disabled':''}>이동해서 정리</button>
      <button class="btn" data-act="run" data-mode="copy" ${busy?'disabled':''}>복사해서 정리 (원본 유지)</button>`;
    if(plan.hasUndo) h+=`<button class="btn ghost" data-act="undo" ${busy?'disabled':''}>↶ 마지막 정리 되돌리기</button>`;
    h+=`</div>`;
  }
  h+=`<div class="msg ${msg.k}">${esc(msg.t)}</div>`;
  $('#pane-run').innerHTML=h;
}
function renderSettings(){
  const c=cfg.categories;
  let h=`<ul class="help">
   <li>폴더 이름은 마음대로 바꾸거나 추가·삭제할 수 있어요. 위에 있는 카테고리가 먼저 검사됩니다.</li>
   <li><b>확장자</b>: 이 확장자면 해당 폴더로 (쉼표로 구분)</li>
   <li><b>파일 이름에 포함된 단어</b>: 채우면 확장자와 단어가 <b>둘 다</b> 맞을 때만 들어가고, 확장자만 쓴 카테고리보다 우선합니다. (예: 영상 확장자 + "final" → 이름에 final이 들어간 영상만)</li>
   <li><b>폴더 이름에 포함된 단어</b>: 이 단어가 들어간 <b>폴더</b>를 통째로 옮김 (예: Media Cache)</li></ul>`;
  h+=c.map((x,i)=>`<div class="cat" data-i="${i}">
    <div class="cat-head"><span class="num">${i+1}</span>
      <input type="text" class="fname" data-f="folder" value="${esc(x.folder)}" placeholder="폴더 이름">
      <button class="mini" data-act="up" title="위로">↑</button><button class="mini" data-act="down" title="아래로">↓</button>
      <button class="mini" data-act="del" title="삭제">✕</button></div>
    <label>확장자<input type="text" data-f="extensions" value="${esc(x.extensions.join(', '))}" placeholder=".mp4, .mov"></label>
    <label>파일 이름에 포함된 단어<input type="text" data-f="keywords" value="${esc(x.keywords.join(', '))}" placeholder="final, 최종"></label>
    <label>폴더 이름에 포함된 단어<input type="text" data-f="dirs" value="${esc(x.dirs.join(', '))}" placeholder="Media Cache, Previews"></label>
    <label class="chk"><input type="checkbox" data-f="matchProjectName" ${x.matchProjectName?'checked':''}> 프로젝트 파일(.prproj)과 이름이 같으면 포함</label>
  </div>`).join('');
  h+=`<div class="row2"><button class="btn" data-act="add">+ 카테고리 추가</button>
    <button class="btn ghost" data-act="reset">기본값으로 복원</button><span class="saved" id="saved"></span></div>
  <div class="fb"><label>분류 못 한 파일을 모을 폴더 (비우면 그대로 둠)
    <input type="text" data-f="fallback" value="${esc(cfg.fallback)}" placeholder="예: 09_ETC"></label></div>`;
  $('#pane-set').innerHTML=h;
}
const splitList=(v,keepSpace)=>v.split(keepSpace?/[,，]/:/[,，\s]+/).map(s=>s.trim()).filter(Boolean);

let saveTimer=null;
function scheduleSave(){
  clearTimeout(saveTimer);
  $('#saved')&&($('#saved').textContent='저장 중…');
  saveTimer=setTimeout(async()=>{
    await api('config',cfg);
    $('#saved')&&($('#saved').textContent='저장됨');
    if(folder) refreshPlan();
  },500);
}
async function refreshPlan(){
  const p=await api('plan',{folder,config:cfg});
  if(p.error){msg={t:p.error,k:'err'};plan=null;}else plan=p;
  renderRun();
}
async function act(a,el){
  if(a==='quit'){await api('quit',{});document.body.innerHTML='<div class="wrap"><p class="empty">종료됐어요. 이 탭을 닫아도 됩니다.</p></div>';return;}
  if(a==='pick'){
    const r=await api('pick',{});
    if(r.path){folder=r.path.replace(/\/$/,'');msg={t:'',k:''};await refreshPlan();}
  }else if(a==='run'||a==='undo'){
    busy=true;msg={t:a==='run'?'정리 중… (큰 파일은 시간이 걸려요)':'되돌리는 중…',k:''};renderRun();
    const r=await api(a,{folder,config:cfg,mode:el.dataset.mode});
    busy=false;
    if(r.error)msg={t:r.error,k:'err'};
    else if(a==='run')msg={t:`완료: ${r.done}개 ${el.dataset.mode==='copy'?'복사':'이동'}`+(r.failed.length?` (실패 ${r.failed.length}: ${r.failed.join(' / ')})`:''),k:r.failed.length?'err':'ok'};
    else msg={t:`${r.undone}개 항목을 원래 위치로 되돌렸어요.`,k:'ok'};
    await refreshPlan();
  }else{
    const cat=el.closest('.cat'),i=cat?+cat.dataset.i:-1,c=cfg.categories;
    if(a==='add'){const n=String(c.length+1).padStart(2,'0');c.push({folder:n+'_NEW',extensions:[],keywords:[],dirs:[],matchProjectName:false});}
    else if(a==='del'){if(!confirm(`'${c[i].folder}' 카테고리를 삭제할까요?`))return;c.splice(i,1);}
    else if(a==='up'&&i>0)[c[i-1],c[i]]=[c[i],c[i-1]];
    else if(a==='down'&&i<c.length-1)[c[i+1],c[i]]=[c[i],c[i+1]];
    else if(a==='reset'){if(!confirm('분류 설정을 기본값으로 되돌릴까요?'))return;cfg=await api('config/reset',{});renderSettings();if(folder)refreshPlan();return;}
    renderSettings();scheduleSave();
  }
}
document.addEventListener('click',e=>{
  const t=e.target.closest('[data-tab]');
  if(t){document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b===t));
    document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('on',p.id==='pane-'+t.dataset.tab));return;}
  const b=e.target.closest('[data-act]');if(b&&!b.disabled)act(b.dataset.act,b);
});
document.addEventListener('input',e=>{
  const f=e.target.dataset.f;if(!f)return;
  if(f==='fallback'){cfg.fallback=e.target.value;scheduleSave();return;}
  const cat=e.target.closest('.cat');if(!cat)return;
  const c=cfg.categories[+cat.dataset.i];
  if(f==='folder')c.folder=e.target.value;
  else if(f==='matchProjectName')c.matchProjectName=e.target.checked;
  else c[f]=splitList(e.target.value,f==='keywords'||f==='dirs');
  scheduleSave();
});
addEventListener('pagehide',()=>navigator.sendBeacon('/api/bye?t='+T));
setInterval(()=>api('ping'),30000);
(async()=>{cfg=await api('config');renderRun();renderSettings();})();
</script></body></html>"""

if __name__ == "__main__":
    main()
