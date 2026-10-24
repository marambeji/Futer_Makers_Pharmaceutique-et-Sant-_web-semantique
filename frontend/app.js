const $ = s => document.querySelector(s);
const escapeHtml = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let molecules = [], catalogue = {}, editing = false;
async function api(path, options={}) {
  const response = await fetch('/api/'+path, {headers:{'Content-Type':'application/json'},...options});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
function report(error) { $('#status').textContent = error.message; }
function table(data) {
  if (!data.rows.length) return '<p class="empty">Aucun résultat dans le graphe.</p>';
  return '<div class="table-wrap"><table><thead><tr>'+data.columns.map(c=>'<th>'+escapeHtml(c)+'</th>').join('')+'</tr></thead><tbody>'+data.rows.map(row=>'<tr>'+data.columns.map(c=>'<td>'+escapeHtml(row[c])+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
}
document.querySelectorAll('nav button').forEach(button=>button.onclick=()=>{
  document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active', b===button));
  document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==button.dataset.view);
  $('#breadcrumb').textContent=button.textContent.trim().replace(/^[^\p{L}]+/u,''); $('#status').textContent='';
});
async function refresh() {
  const [stats,items,relations]=await Promise.all([api('overview'),api('molecules'),api('catalogue')]);
  molecules=items; catalogue=relations;
  $('#stats').innerHTML=[['Molécules',stats.molecules,'⌬'],['Effets secondaires',stats.effets,'✧'],['Essais cliniques',stats.essais,'▤'],['Triplets RDF',stats.triples,'◇']].map(([name,value,icon])=>`<div class="stat"><small>${name}</small><b>${value}</b><span>${icon}</span></div>`).join('');
  renderCards(); renderAdmin();
  for(const [id,key] of [['#mol-effects','effets'],['#mol-contra','contre_indications']]) $(id).innerHTML=catalogue[key].map(i=>`<option value="${escapeHtml(i.id)}">${escapeHtml(i.nom)}</option>`).join('');
}
function renderCards(){
  const term=$('#filter').value.toLocaleLowerCase('fr');
  const items=molecules.filter(m=>[m.nom,...m.effets,...m.contre_indications].join(' ').toLocaleLowerCase('fr').includes(term));
  $('#molecule-cards').innerHTML=items.length?items.map(m=>`<article class="molecule-card"><div class="symbol">⌬</div><h3>${escapeHtml(m.nom)}</h3><small>${escapeHtml(m.formule)} · ${escapeHtml(m.id)}</small><p>EFFETS SECONDAIRES</p>${m.effets.map(e=>`<span class="pill">${escapeHtml(e)}</span>`).join('')||'<small>Aucun renseigné</small>'}<p>CONTRE-INDICATIONS<br>${escapeHtml(m.contre_indications.join(', ')||'Aucune renseignée')}</p></article>`).join(''):'<p>Aucune molécule trouvée.</p>';
}
$('#filter').oninput=renderCards;
$('#ask-form').onsubmit=async event=>{
  event.preventDefault(); const button=event.submitter; button.disabled=true; $('#status').textContent='';
  try{const data=await api('ask',{method:'POST',body:JSON.stringify({question:$('#question').value})}); $('#ask-result').className='';$('#ask-result').innerHTML=table(data);$('#result-count').textContent=data.rows.length+' RÉSULTAT(S)';$('#generated-query').textContent=data.sparql;$('#trace-info').textContent=`Intention : ${data.intent} · Entités : ${data.entities.join(', ')||'aucune'} · Tokens : ${data.tokens.join(' / ')} · Racines : ${data.stems.join(' / ')}`;}
  catch(error){report(error);$('#ask-result').className='';$('#ask-result').textContent='La question n’a pas pu être exécutée.';$('#result-count').textContent='ERREUR';$('#generated-query').textContent='';$('#trace-info').textContent='';}finally{button.disabled=false;}
};
document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>{$('#question').value=b.dataset.question;$('#ask-form').requestSubmit($('#ask-form button[type="submit"]'));});
$('#run-query').onclick=async()=>{ $('#status').textContent='';try{$('#query-result').innerHTML=table(await api('sparql',{method:'POST',body:JSON.stringify({query:$('#sparql-query').value})}));}catch(e){$('#query-result').textContent='Requête non exécutée.';report(e);}};
function renderAdmin(){
  $('#admin-list').innerHTML=molecules.map(m=>`<div class="admin-item"><span>${escapeHtml(m.nom)}</span><button data-edit="${escapeHtml(m.id)}">Modifier</button><button class="danger" data-delete="${escapeHtml(m.id)}">Supprimer</button></div>`).join('');
  document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{
    const m=molecules.find(m=>m.id===b.dataset.edit);editing=true;$('#admin-title').textContent='Modifier '+m.nom;$('#mol-id').value=m.id;$('#mol-id').disabled=true;$('#mol-name').value=m.nom;$('#mol-formula').value=m.formule;
    for(const [id,names] of [['#mol-effects',m.effets],['#mol-contra',m.contre_indications]]) Array.from($(id).options).forEach(o=>o.selected=names.includes(o.text));
  });
  document.querySelectorAll('[data-delete]').forEach(b=>b.onclick=async()=>{
    if(!confirm('Supprimer cette molécule et ses relations ?'))return;
    try{const data=await api('molecules/'+encodeURIComponent(b.dataset.delete),{method:'DELETE'});$('#crud-query').textContent=data.sparql;resetForm();await refresh();$('#status').textContent='Molécule supprimée.';}catch(e){report(e);}
  });
}
function resetForm(){editing=false;$('#molecule-form').reset();$('#mol-id').disabled=false;$('#admin-title').textContent='Ajouter une molécule';}
$('#reset-form').onclick=resetForm;
$('#molecule-form').onsubmit=async e=>{
  e.preventDefault();const body={id:$('#mol-id').value,nom:$('#mol-name').value,formule:$('#mol-formula').value,effets:Array.from($('#mol-effects').selectedOptions,o=>o.value),contre_indications:Array.from($('#mol-contra').selectedOptions,o=>o.value)};
  try{const data=await api('molecules'+(editing?'/'+encodeURIComponent(body.id):''),{method:editing?'PUT':'POST',body:JSON.stringify(body)});$('#crud-query').textContent=data.sparql;resetForm();await refresh();$('#status').textContent='Modification enregistrée dans le graphe RDF.';}catch(error){report(error);}
};
refresh().catch(report);
