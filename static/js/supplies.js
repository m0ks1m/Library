function normalizePhone(v){const d=(v||'').replace(/\D/g,'');if(d.length===11&&(d[0]==='7'||d[0]==='8'))return '7'+d.slice(1);return d}
function fmt(v){const d=normalizePhone(v);if(d.length!==11)return v;return `+7 (${d.slice(1,4)}) ${d.slice(4,7)}-${d.slice(7,9)}-${d.slice(9,11)}`}

async function loadSuppliers(){
  const r=await fetch('/api/suppliers'); const d=await r.json();
  const body=document.getElementById('suppliers-body'); body.innerHTML='';
  (d.suppliers||[]).forEach(s=>{const tr=document.createElement('tr'); tr.innerHTML=`<td>${s.id}</td><td>${s.name||''}</td><td>${s.contact_person||''}</td><td>${fmt(s.phone||'')}</td><td>${s.email||''}</td><td>${[s.city,s.street,s.house,s.apartment].filter(Boolean).join(', ')}</td><td>${s.is_active? 'active':'inactive'}</td><td><button class='btn btn-danger' onclick='deactivateSupplier(${s.id})'>Деактивировать</button></td>`; body.appendChild(tr);});
}

async function saveSupplier(){
 const payload={name:val('supplier-name'),contact_person:val('supplier-contact-person'),phone:normalizePhone(val('supplier-phone')),email:val('supplier-email').toLowerCase(),city:val('supplier-city'),street:val('supplier-street'),house:val('supplier-house'),apartment:val('supplier-apartment'),comment:val('supplier-comment'),is_active:true};
 const r=await fetch('/api/suppliers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); if(!r.ok){alert('Ошибка сохранения');return;} await loadSuppliers();
}
async function deactivateSupplier(id){await fetch(`/api/suppliers/${id}`,{method:'DELETE'}); await loadSuppliers();}

async function saveContract(){
 const payload={contract_number:val('contract-number'),signed_at:val('contract-signed'),supplier_id:Number(val('contract-supplier')),start_date:val('contract-start'),end_date:val('contract-end'),amount_or_terms:val('contract-terms'),comment:val('contract-comment')};
 await fetch('/api/contracts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); await loadContracts();
}
async function loadContracts(){const r=await fetch('/api/contracts'); const d=await r.json(); document.getElementById('contracts-list').textContent=JSON.stringify(d.contracts||[],null,2)}
async function loadInvoices(){const r=await fetch('/api/invoices'); const d=await r.json(); document.getElementById('invoices-list').textContent=JSON.stringify(d.invoices||[],null,2)}
async function loadAcceptance(){const r=await fetch('/api/acceptance-acts'); const d=await r.json(); document.getElementById('acceptance-list').textContent=JSON.stringify(d.acts||[],null,2)}
async function loadWriteoff(){const r=await fetch('/api/writeoff-acts'); const d=await r.json(); document.getElementById('writeoff-list').textContent=JSON.stringify(d.acts||[],null,2)}
function val(id){return document.getElementById(id).value.trim()}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('supplier-phone')?.addEventListener('input',e=>e.target.value=fmt(e.target.value));loadSuppliers();loadContracts();loadInvoices();loadAcceptance();loadWriteoff();});
