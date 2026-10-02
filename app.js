const API = window.location.origin + "/api";
async function api(path, options={}) {
  const r = await fetch(API + path, {
    headers: {"Content-Type":"application/json"},
    ...options
  });
  return r.json();
}

function toast(msg){
  const el=document.getElementById("toast");
  el.textContent=msg; el.style.display="block";
  setTimeout(()=>el.style.display="none",2200);
}

function statusLabel(s){return s==="running" ? "🟢 يعمل" : "⏸ متوقف"}

async function loadAgent(){
  const a=await api("/agent");
  document.getElementById("agentStatus").textContent=statusLabel(a.status);
  document.getElementById("toggle").textContent=a.status==="running"?"إيقاف الوكيل":"تشغيل الوكيل";
  document.getElementById("toggle").onclick=async()=>{
    await api("/agent/toggle",{method:"POST",body:JSON.stringify({status:a.status==="running"?"paused":"running"})});
    loadAll();
  };
}

async function loadTasks(){
  const data=await api("/tasks");
  document.getElementById("taskCount").textContent=data.tasks.length;
  const box=document.getElementById("tasks");
  box.innerHTML="";
  data.tasks.forEach(t=>{
    const status = {
      available:"متاحة", review:"بانتظار المراجعة", completed:"مكتملة"
    }[t.status] || t.status;
    box.innerHTML += `
      <div class="task">
        <div class="taskTop">
          <div><h3>${t.title}</h3><div class="muted">${t.description}</div></div>
          <span class="badge">${status}</span>
        </div>
        <p><b>المقابل:</b> $${t.reward.toFixed(2)} &nbsp; <b>المنصة:</b> ${t.platform}</p>
        <div class="actions">
          ${t.status==="available" ? `<button onclick="analyze(${t.id})">تحليل المهمة</button>` : ""}
          ${t.status==="review" ? `<button onclick="approve(${t.id})">موافقة وتجهيز التسليم</button>` : ""}
        </div>
      </div>`;
  });
}

async function analyze(id){
  const r=await api("/tasks/analyze",{method:"POST",body:JSON.stringify({task_id:id})});
  if(!r.ok){toast("حدث خطأ");return}
  if(r.decision==="accepted"){
    const x=await api("/tasks/execute",{method:"POST",body:JSON.stringify({task_id:id})});
    alert("نتيجة تجريبية للمراجعة:\\n\\n"+x.result);
  }else toast(r.reason);
  loadAll();
}

async function approve(id){
  const ok=confirm("هل تريد الموافقة على النتيجة وتجهيز المهمة للتسليم؟");
  if(!ok)return;
  const r=await api("/tasks/approve",{method:"POST",body:JSON.stringify({task_id:id})});
  toast(r.ok?"تمت الموافقة":"تعذر تنفيذ العملية");
  loadAll();
}

async function loadEarnings(){
  const e=await api("/earnings");
  document.getElementById("total").textContent=`$${e.total.toFixed(2)}`;
  document.getElementById("pending").textContent=`$${e.pending.toFixed(2)}`;
}

async function loadLogs(){
  const d=await api("/logs");
  document.getElementById("logs").innerHTML=d.logs.map(x=>
    `<div class="log"><b>${x.time}</b> — ${x.message}</div>`
  ).join("");
}

async function loadAll(){
  try{await Promise.all([loadAgent(),loadTasks(),loadEarnings(),loadLogs()]);}
  catch(e){toast("شغّل الـ Backend أولًا");}
}
loadAll();
