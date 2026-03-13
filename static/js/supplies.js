let invoiceItems = [];
let acceptItems = [];
let writeoffItems = [];

async function api(url, options={}) {
  const r = await fetch(url, {headers:{'Content-Type':'application/json'}, ...options});
  const j = await r.json();
  if(!r.ok || j.success===false) throw new Error(j.error || 'Ошибка API');
  return j;
}

async function loadLookups(){
  const suppliers = (await api('/api/suppliers')).suppliers;
  const contracts = (await api('/api/contracts')).contracts;
  const books = (await api('/api/books/all')).books;
  const copies = (await api('/api/book-copies/available')).copies;

  const supplierOptions = suppliers.map(s=>`<option value="${s.id}">${s.name}</option>`).join('');
  ['contract-supplier','invoice-supplier','accept-supplier'].forEach(id=>{ const el=document.getElementById(id); if(el) el.innerHTML=supplierOptions; });
  const contractOptions = contracts.map(c=>`<option value="${c.id}">${c.contract_number} (${c.supplier_name})</option>`).join('');
  ['invoice-contract','accept-contract'].forEach(id=>{ const el=document.getElementById(id); if(el) el.innerHTML=contractOptions; });
  const bookOptions = books.map(b=>`<option value="${b.id}">${b.title}</option>`).join('');
  ['invoice-book','accept-book'].forEach(id=>{ const el=document.getElementById(id); if(el) el.innerHTML=bookOptions; });
  const copyOptions = copies.map(c=>`<option value="${c.id}">${c.inventory_code} — ${c.book_name}</option>`).join('');
  document.getElementById('writeoff-copy').innerHTML = copyOptions;
}

async function refreshAll(){
  await loadSuppliers(); await loadContracts(); await loadInvoices(); await loadAcceptanceActs(); await loadWriteoffActs(); await loadLookups();
}

document.addEventListener('DOMContentLoaded', refreshAll);

async function loadSuppliers(){
  const data = await api('/api/suppliers');
  document.getElementById('suppliers-body').innerHTML = data.suppliers.map(s=>`<tr><td>${s.id}</td><td>${s.name}</td><td>${s.contact_person||''}</td><td>${s.phone||''}</td><td>${s.email||''}</td><td>${s.is_active?'Да':'Нет'}</td><td><button class="btn btn-danger" onclick="deactivateSupplier(${s.id})">Деактив.</button></td></tr>`).join('');
}
async function createSupplier(){
  await api('/api/suppliers',{method:'POST', body:JSON.stringify({name:sv('supplier-name'), contact_person:sv('supplier-contact-person'), phone:sv('supplier-phone'), email:sv('supplier-email'), address:sv('supplier-address'), commentary:sv('supplier-commentary'), is_active:true})});
  await refreshAll();
}
async function deactivateSupplier(id){ await api(`/api/suppliers/${id}`,{method:'DELETE'}); await refreshAll(); }

async function loadContracts(){
  const data = await api('/api/contracts');
  document.getElementById('contracts-body').innerHTML = data.contracts.map(c=>`<tr><td>${c.id}</td><td>${c.contract_number}</td><td>${c.supplier_name}</td><td>${c.start_date||''} - ${c.end_date||''}</td><td>${c.terms_note||''}</td></tr>`).join('');
}
async function createContract(){
  await api('/api/contracts',{method:'POST', body:JSON.stringify({contract_number:sv('contract-number'),contract_date:sv('contract-date'),supplier_id:Number(sv('contract-supplier')),start_date:sv('contract-start'),end_date:sv('contract-end'),terms_note:sv('contract-terms'),commentary:sv('contract-comment')})});
  await refreshAll();
}

function addInvoiceItem(){ invoiceItems.push({book_id:Number(sv('invoice-book')), quantity:Number(sv('invoice-qty')), unit_price:Number(sv('invoice-price'))}); renderSimpleItems('invoice-items-body', invoiceItems); }
async function createInvoice(){
  await api('/api/invoices',{method:'POST', body:JSON.stringify({invoice_number:sv('invoice-number'),invoice_date:sv('invoice-date'),supplier_id:Number(sv('invoice-supplier')),contract_id:Number(sv('invoice-contract')),commentary:sv('invoice-comment'),items:invoiceItems})});
  invoiceItems=[]; renderSimpleItems('invoice-items-body', invoiceItems); await refreshAll();
}
async function loadInvoices(){
  const data = await api('/api/invoices');
  document.getElementById('invoices-body').innerHTML = data.invoices.map(i=>`<tr><td>${i.id}</td><td>${i.invoice_number}</td><td>${i.supplier_name}</td><td>${i.total_amount}</td></tr>`).join('');
}

function addAcceptItem(){ acceptItems.push({book_id:Number(sv('accept-book')), quantity:Number(sv('accept-qty')), unit_price:Number(sv('accept-price'))}); renderSimpleItems('accept-items-body', acceptItems); }
async function createAcceptanceAct(){
  await api('/api/acceptance-acts',{method:'POST', body:JSON.stringify({act_number:sv('accept-number'),act_date:sv('accept-date'),supplier_id:Number(sv('accept-supplier')),contract_id:Number(sv('accept-contract')),commentary:sv('accept-comment'),items:acceptItems})});
  acceptItems=[]; renderSimpleItems('accept-items-body', acceptItems); await refreshAll();
}
async function loadAcceptanceActs(){
  const data = await api('/api/acceptance-acts');
  document.getElementById('accept-body').innerHTML = data.acts.map(a=>`<tr><td>${a.id}</td><td>${a.act_number}</td><td>${a.supplier_name}</td><td>${a.total_amount}</td><td>${a.status}</td></tr>`).join('');
}

function addWriteoffItem(){ writeoffItems.push({copy_id:Number(sv('writeoff-copy')), reason:sv('writeoff-reason')}); document.getElementById('writeoff-items-body').innerHTML = writeoffItems.map(i=>`<tr><td>${i.copy_id}</td><td>${i.reason}</td></tr>`).join(''); }
async function createWriteoffAct(){
  await api('/api/writeoff-acts',{method:'POST', body:JSON.stringify({act_number:sv('writeoff-number'),act_date:sv('writeoff-date'),basis:sv('writeoff-basis'),commentary:sv('writeoff-comment'),items:writeoffItems})});
  writeoffItems=[]; document.getElementById('writeoff-items-body').innerHTML=''; await refreshAll();
}
async function loadWriteoffActs(){
  const data = await api('/api/writeoff-acts');
  document.getElementById('writeoff-body').innerHTML = data.acts.map(a=>`<tr><td>${a.id}</td><td>${a.act_number}</td><td>${a.act_date}</td><td>${a.basis||''}</td><td>${a.status}</td></tr>`).join('');
}

function renderSimpleItems(id, items){ document.getElementById(id).innerHTML = items.map(i=>`<tr><td>${i.book_id}</td><td>${i.quantity}</td><td>${i.unit_price}</td></tr>`).join(''); }
function sv(id){ return document.getElementById(id).value; }
