document.addEventListener('DOMContentLoaded', () => {
  loadSuppliers(); loadContracts(); loadAcceptanceActs(); loadWriteoffActs();
});

function table(headers, rows) {
  return `<table class="search-results"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c ?? ''}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

async function createSupplier() {
  const payload = {name: v('supplier-name'), contact_person: v('supplier-contact'), phone: v('supplier-phone'), email: v('supplier-email'), address: v('supplier-address'), comment: v('supplier-comment'), is_active: 1};
  await fetch('/api/suppliers', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  loadSuppliers();
}
async function loadSuppliers() {
  const d = await (await fetch('/api/suppliers')).json();
  document.getElementById('suppliers-list').innerHTML = table(['ID','Название','Контакт','Телефон','Email','Статус'], (d.suppliers||[]).map(s=>[s.id,s.name,s.contact_person,s.phone,s.email,s.is_active?'active':'inactive']));
}

async function createContract() {
  const payload = {contract_number:v('contract-number'), signed_date:v('contract-signed'), supplier_id:Number(v('contract-supplier-id')), start_date:v('contract-start'), end_date:v('contract-end'), terms:v('contract-terms')};
  await fetch('/api/contracts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  loadContracts();
}
async function loadContracts() {
  const d = await (await fetch('/api/contracts')).json();
  document.getElementById('contracts-list').innerHTML = table(['ID','Номер','Поставщик','Дата','Период'], (d.contracts||[]).map(c=>[c.id,c.contract_number,c.supplier_name,c.signed_date,`${c.start_date||''} - ${c.end_date||''}`]));
}

async function createAcceptanceAct() {
  const payload = {act_number:v('acc-number'), date:v('acc-date'), supplier_id:Number(v('acc-supplier-id')), contract_id:Number(v('acc-contract-id')||0)||null, items:[{book_id:Number(v('acc-book-id')), quantity:Number(v('acc-qty')||1), price:0}]};
  await fetch('/api/acceptance-acts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  loadAcceptanceActs();
}
async function loadAcceptanceActs() {
  const d = await (await fetch('/api/acceptance-acts')).json();
  document.getElementById('acceptance-list').innerHTML = table(['ID','Номер','Дата','Поставщик','Комментарий'], (d.acts||[]).map(a=>[a.id,a.act_number,a.date,a.supplier_name,a.comment]));
}

async function createWriteoffAct() {
  const payload = {act_number:v('wo-number'), date:v('wo-date'), basis:v('wo-basis'), comment:v('wo-comment'), items:[{book_copy_id:Number(v('wo-copy-id')), reason:v('wo-reason')}]};
  await fetch('/api/writeoff-acts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  loadWriteoffActs();
}
async function loadWriteoffActs() {
  const d = await (await fetch('/api/writeoff-acts')).json();
  document.getElementById('writeoff-list').innerHTML = table(['ID','Номер','Дата','Основание','Комментарий'], (d.acts||[]).map(a=>[a.id,a.act_number,a.date,a.basis,a.comment]));
}

function v(id){return document.getElementById(id).value.trim();}
