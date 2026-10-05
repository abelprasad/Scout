# Generic mission dashboard: FastAPI app factory with a schema-driven UI.
# The mission plugin supplies list_fields, status options, and titles.
# Zero domain logic here: everything renders from the mission spec.
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
from datetime import datetime, timedelta


def _serialize_row(model, row):
    out = {}
    for c in model.__table__.columns:
        v = getattr(row, c.name)
        out[c.name] = v.isoformat() if isinstance(v, datetime) else v
    return out


def create_dashboard_app(mission=None):
    if mission is None:
        from core.mission import load_mission
        mission = load_mission()

    app = FastAPI(title=mission.dashboard_title)
    model = mission.model
    FIELDS = mission.list_fields

    # ---------- API ----------

    @app.get("/api/stats")
    def get_stats():
        session = mission.get_session()
        try:
            total = session.query(model).count()
            week_ago = datetime.now() - timedelta(days=7)
            recent = 0
            if mission.discovered_field and hasattr(model, mission.discovered_field):
                col = getattr(model, mission.discovered_field)
                recent = session.query(model).filter(col >= week_ago).count()
            status_counts = {}
            if mission.status_field:
                for opt in mission.status_options:
                    status_counts[opt] = session.query(model).filter(
                        getattr(model, mission.status_field) == opt).count()
            return {"total": total, "this_week": recent, "status_counts": status_counts}
        finally:
            session.close()

    @app.get("/api/items")
    def get_items(search: Optional[str] = None, status: Optional[str] = None,
                  sort: Optional[str] = "score", limit: int = 50):
        from sqlalchemy import or_
        session = mission.get_session()
        try:
            q = session.query(model)
            if search and mission.searchable_fields:
                conds = [getattr(model, f).contains(search)
                         for f in mission.searchable_fields if hasattr(model, f)]
                if conds:
                    q = q.filter(or_(*conds))
            if status and mission.status_field:
                q = q.filter(getattr(model, mission.status_field) == status)
            score_col = getattr(model, mission.score_field, None)
            if sort == "score" and score_col is not None:
                q = q.order_by(score_col.desc())
            elif sort == "oldest":
                q = q.order_by(model.id.asc())
            else:
                q = q.order_by(model.id.desc())
            rows = q.limit(limit).all()
            return [_serialize_row(model, r) for r in rows]
        finally:
            session.close()

    @app.post("/api/items")
    def create_item(data: dict):
        session = mission.get_session()
        try:
            cols = set(c.name for c in model.__table__.columns) - {"id"}
            row = model(**{k: v for k, v in data.items() if k in cols})
            session.add(row)
            session.commit()
            return {"success": True, "id": row.id}
        finally:
            session.close()

    @app.put("/api/items/{item_id}")
    def update_item(item_id: int, data: dict):
        session = mission.get_session()
        try:
            row = session.query(model).get(item_id)
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = set(c.name for c in model.__table__.columns) - {"id"}
            for k, v in data.items():
                if k in cols:
                    setattr(row, k, v)
            session.commit()
            return {"success": True}
        finally:
            session.close()

    @app.delete("/api/items/{item_id}")
    def delete_item(item_id: int):
        session = mission.get_session()
        try:
            row = session.query(model).get(item_id)
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            session.delete(row)
            session.commit()
            return {"success": True}
        finally:
            session.close()

    @app.post("/api/items/{item_id}/status")
    def set_status(item_id: int, data: dict):
        if not mission.status_field:
            raise HTTPException(status_code=400, detail="Mission has no status workflow")
        new_status = data.get("status")
        if new_status not in mission.status_options:
            raise HTTPException(status_code=400, detail="Invalid status")
        session = mission.get_session()
        try:
            row = session.query(model).get(item_id)
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            setattr(row, mission.status_field, new_status)
            mission.on_status_change(row, new_status, session)
            session.commit()
            return {"success": True}
        finally:
            session.close()

    @app.post("/api/run-mission")
    def run_mission():
        import httpx
        try:
            r = httpx.post("http://localhost:8000/run-workflow", timeout=120)
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ---------- UI ----------

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        return render_html(mission)

    return app


def render_html(mission):
    fields_json = json.dumps(mission.list_fields)
    status_json = json.dumps(mission.status_options)
    html = _TEMPLATE
    html = html.replace("__DASHBOARD_TITLE__", mission.dashboard_title)
    html = html.replace("__MISSION_DISPLAY__", mission.display_name)
    html = html.replace("__MISSION_DESC__", mission.description)
    html = html.replace("__FIELDS_JSON__", fields_json)
    html = html.replace("__STATUS_OPTIONS_JSON__", status_json)
    html = html.replace("__STATUS_FIELD__", mission.status_field or "")
    html = html.replace("__HAS_STATUS__", "true" if mission.status_field else "false")
    return html


_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__DASHBOARD_TITLE__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a0a;color:#fafafa;font-family:-apple-system,BlinkMacSystemFont,sans-serif}
.header{background:#18181b;border-bottom:1px solid #27272a;padding:24px}
.header h1{font-size:24px}.header p{color:#71717a;font-size:14px;margin-top:4px}
.container{max-width:1100px;margin:0 auto;padding:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:24px}
.stat{background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center}
.stat .n{font-size:28px;font-weight:700}.stat .l{font-size:11px;color:#71717a;text-transform:uppercase;margin-top:4px}
.toolbar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.toolbar input,.toolbar select{background:#18181b;border:1px solid #27272a;color:#fafafa;border-radius:6px;padding:8px 12px;font-size:14px}
.toolbar input{flex:1;min-width:200px}
.btn{background:#fafafa;color:#0a0a0a;border:none;border-radius:6px;padding:8px 16px;font-weight:600;cursor:pointer;font-size:14px}
.btn-sm{padding:4px 10px;font-size:12px}
.btn-secondary{background:#27272a;color:#fafafa}
.btn-danger{background:#3f1d1d;color:#fca5a5}
.btn-success{background:#14532d;color:#bbf7d0}
.items{background:#18181b;border:1px solid #27272a;border-radius:8px;overflow:hidden}
.items-header{padding:14px 20px;border-bottom:1px solid #27272a;font-weight:600}
.item{display:flex;justify-content:space-between;gap:16px;padding:14px 20px;border-bottom:1px solid #1c1c1f}
.item:last-child{border-bottom:none}
.item:hover{background:#1c1c1f}
.item .title{font-weight:600;font-size:15px}
.item .subtitle{color:#a1a1aa;font-size:13px;margin-top:2px}
.item .meta{color:#71717a;font-size:12px;margin-top:4px}
.item .url{color:#7dd3fc;font-size:13px;text-decoration:none}
.item-actions{display:flex;gap:6px;align-items:flex-start;flex-wrap:wrap;justify-content:flex-end;min-width:220px}
.score-badge{padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;color:#fff}
.score-high{background:#16a34a}.score-mid{background:#ca8a04}.score-low{background:#52525b}
.status-pill{padding:3px 10px;border-radius:12px;font-size:11px;background:#27272a;color:#a1a1aa;text-transform:uppercase}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:10}
.modal-content{background:#18181b;border:1px solid #27272a;border-radius:8px;max-width:520px;margin:60px auto;padding:24px}
.modal-content h3{margin-bottom:16px}
.modal-content label{display:block;font-size:12px;color:#71717a;margin:10px 0 4px}
.modal-content input,.modal-content textarea{width:100%;background:#0a0a0a;border:1px solid #27272a;color:#fafafa;border-radius:6px;padding:8px 12px;font-size:14px}
.modal-actions{margin-top:16px;display:flex;gap:8px;justify-content:flex-end}
.empty{padding:40px;text-align:center;color:#71717a}
</style></head>
<body>
<div class="header"><div class="container" style="padding:0">
<h1>__DASHBOARD_TITLE__</h1><p>__MISSION_DESC__</p></div></div>
<div class="container">
<div class="stats" id="stats"></div>
<div class="toolbar">
<input id="search" placeholder="Search..." oninput="loadItems()">
<select id="statusFilter" onchange="loadItems()"><option value="">All statuses</option></select>
<select id="sortBy" onchange="loadItems()">
<option value="score">Best score</option><option value="newest">Newest</option><option value="oldest">Oldest</option>
</select>
<button class="btn" onclick="runMission()">Run mission now</button>
<button class="btn btn-secondary" onclick="showAddModal()">Add item</button>
</div>
<div class="items"><div class="items-header" id="itemsHeader">Items</div><div id="item-list">Loading...</div></div>
</div>
<div class="modal" id="editModal"><div class="modal-content"><h3 id="modalTitle">Edit item</h3><div id="modalFields"></div>
<div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal()">Cancel</button><button class="btn" onclick="saveModal()">Save</button></div></div></div>
<script>
const FIELDS = __FIELDS_JSON__;
const STATUS_OPTIONS = __STATUS_OPTIONS_JSON__;
const STATUS_FIELD = "__STATUS_FIELD__";
const HAS_STATUS = __HAS_STATUS__;
let currentItems = [], editingId = null;

const titleF = FIELDS.find(f=>f.type==="title")||FIELDS[0];
const subF = FIELDS.find(f=>f.type==="subtitle");
const metaFs = FIELDS.filter(f=>f.type==="meta");
const linkF = FIELDS.find(f=>f.type==="link");
const scoreF = FIELDS.find(f=>f.type==="score");
const dateF = FIELDS.find(f=>f.type==="date");
const ageF = FIELDS.find(f=>f.type==="age");

function fmtStatus(s){return (s||"").replace(/_/g," ");}
function scoreClass(v){v=parseFloat(v)||0;return v>=7?"score-high":v>=4?"score-mid":"score-low";}

async function loadStats(){
  const r = await fetch("/api/stats"); const s = await r.json();
  let h = '<div class="stat"><div class="n">'+s.total+'</div><div class="l">Total</div></div>';
  h += '<div class="stat"><div class="n">'+s.this_week+'</div><div class="l">This week</div></div>';
  for(const [k,v] of Object.entries(s.status_counts||{})){
    h += '<div class="stat"><div class="n">'+v+'</div><div class="l">'+fmtStatus(k)+'</div></div>';
  }
  document.getElementById("stats").innerHTML = h;
  const sf = document.getElementById("statusFilter");
  sf.innerHTML = '<option value="">All statuses</option>' + STATUS_OPTIONS.map(o=>'<option value="'+o+'">'+fmtStatus(o)+'</option>').join("");
}
async function loadItems(){
  const q = new URLSearchParams({search:document.getElementById("search").value,
    status:document.getElementById("statusFilter").value,
    sort:document.getElementById("sortBy").value, limit:100});
  const r = await fetch("/api/items?"+q); const items = await r.json();
  currentItems = items; renderItems(items); loadStats();
  document.getElementById("itemsHeader").textContent = "Items ("+items.length+")";
}
function renderItems(items){
  const el = document.getElementById("item-list");
  if(!items.length){el.innerHTML='<div class="empty">No items found</div>';return;}
  el.innerHTML = items.map(it=>{
    const meta = metaFs.map(f=>it[f.key]).filter(Boolean).join(" · ");
    let metaLine = meta;
    if(ageF && it[ageF.key]!=null) metaLine += (metaLine?" · ":"")+"Posted "+it[ageF.key]+"d ago";
    if(dateF && it[dateF.key]) metaLine += (metaLine?" · ":"")+"Found "+new Date(it[dateF.key]).toLocaleDateString();
    let actions = '<button class="btn btn-sm btn-secondary" onclick="showEditModal('+it.id+')">Edit</button>';
    if(HAS_STATUS && STATUS_FIELD){
      const cur = it[STATUS_FIELD]||"";
      const next = STATUS_OPTIONS.find(o=>o!==cur);
      if(next) actions += '<button class="btn btn-sm btn-success" onclick="setStatus('+it.id+',\''+next+'\')">→ '+fmtStatus(next)+'</button>';
    }
    actions += '<button class="btn btn-sm btn-danger" onclick="deleteItem('+it.id+')">Delete</button>';
    return '<div class="item"><div><div class="title">'+esc(it[titleF.key]||"")+'</div>'
      + (subF?'<div class="subtitle">'+esc(it[subF.key]||"")+'</div>':"")
      + (metaLine?'<div class="meta">'+esc(metaLine)+'</div>':"")
      + (linkF&&it[linkF.key]?'<div><a class="url" href="'+esc(it[linkF.key])+'" target="_blank">Open link</a></div>':"")
      + '</div><div class="item-actions">'
      + (scoreF?'<span class="score-badge '+scoreClass(it[scoreF.key])+'">'+(parseFloat(it[scoreF.key])||0).toFixed(1)+'</span>':"")
      + (HAS_STATUS&&STATUS_FIELD?'<span class="status-pill">'+fmtStatus(it[STATUS_FIELD]||"")+'</span>':"")
      + actions + '</div></div>';
  }).join("");
}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function editableFields(){return FIELDS.filter(f=>["title","subtitle","meta","link","text"].includes(f.type));}
function showAddModal(){editingId=null;document.getElementById("modalTitle").textContent="Add item";
  document.getElementById("modalFields").innerHTML = editableFields().map(f=>
    '<label>'+f.label+'</label><input id="f_'+f.key+'">').join("");
  document.getElementById("editModal").style.display="block";}
function showEditModal(id){const it=currentItems.find(x=>x.id===id);if(!it)return;editingId=id;
  document.getElementById("modalTitle").textContent="Edit item";
  document.getElementById("modalFields").innerHTML = editableFields().map(f=>
    '<label>'+f.label+'</label><input id="f_'+f.key+'" value="'+esc(it[f.key]||"")+'">').join("");
  document.getElementById("editModal").style.display="block";}
function closeModal(){document.getElementById("editModal").style.display="none";}
async function saveModal(){
  const data={}; editableFields().forEach(f=>{data[f.key]=document.getElementById("f_"+f.key).value;});
  const url = editingId?"/api/items/"+editingId:"/api/items";
  const method = editingId?"PUT":"POST";
  await fetch(url,{method,headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  closeModal(); loadItems();
}
async function deleteItem(id){if(!confirm("Delete this item?"))return;
  await fetch("/api/items/"+id,{method:"DELETE"}); loadItems();}
async function setStatus(id,status){
  await fetch("/api/items/"+id+"/status",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({status})});
  loadItems();}
async function runMission(){
  if(!confirm("Run the mission workflow now?"))return;
  const r = await fetch("/api/run-mission",{method:"POST"}); const j = await r.json();
  alert(j.success?"Workflow finished":"Failed: "+(j.detail||j.error||"unknown"));
  loadItems();}
loadItems();
</script></body></html>
"""


if __name__ == "__main__":
    import uvicorn
    from core.mission import load_mission
    uvicorn.run(create_dashboard_app(load_mission()), host="0.0.0.0", port=8001)
