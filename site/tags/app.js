(async function () {
  const T = globalThis.OKGTags, $ = id => document.getElementById(id);
  try {
    async function get(name) {
      const response = await fetch(`../data/${name}`, {cache: "no-cache"});
      if (!response.ok) { // Local repository preview has data at its root.
        const local = await fetch(`../../data/${name}`, {cache: "no-cache"});
        if (!local.ok) throw new Error(`Could not load ${name}`); return local.json();
      }
      return response.json();
    }
    const [vocab, resourcePayload, softwarePayload, jobsPayload] = await Promise.all([get("tag-vocabularies.json"),get("ontologies.json"),get("software.json"),get("jobs/jobs.json")]);
    const index = T.termIndex(vocab), resources=resourcePayload.items, software=softwarePayload.items, jobs=T.eligibleJobs(jobsPayload);
    const selected=T.selections(new URLSearchParams(location.search));
    for (const dim of T.dimensions) {
      for (const term of vocab.terms.filter(t=>t.dimension===dim)) {
        const option=document.createElement("option");option.value=term.id;option.textContent=(term.broader.length ? "↳ " : "")+term.label;option.selected=selected[dim].includes(term.id);$(dim).append(option);
      }
      $(dim).addEventListener("change",()=>{ selected[dim]=[...$(dim).selectedOptions].map(o=>o.value); render(); });
    }
    $("tool-search").addEventListener("input",()=>{
      const query=$("tool-search").value.trim().toLocaleLowerCase();
      for(const option of $("tools").options) option.hidden=!option.selected && !option.textContent.toLocaleLowerCase().includes(query);
    });
    $("clear").onclick=()=>{$("tool-search").value="";for(const option of $("tools").options)option.hidden=false;for(const dim of T.dimensions){selected[dim]=[];for(const o of $(dim).options)o.selected=false;}render();};
    $("dimension").onchange=render;
    function showRecords(id, rows, job=false) {
      $(id).replaceChildren();
      for(const item of rows.slice(0,20)) {
        const card=document.createElement("article");card.className="record";
        const title=document.createElement("h3"),link=document.createElement("a");link.textContent=item.title;link.href=job?item.sourceUrl:((index.get(index.pages.get(item.canonicalUrl))?.catalogPages || []).includes(item.canonicalUrl)?item.canonicalUrl:item.wikidataId);title.append(link);card.append(title);
        const text=document.createElement("p");text.textContent=job?item.hiringOrganization:(item.description||"No description available.");card.append(text);
        T.tagChips(card,item,document);$(id).append(card);
      }
      if(!rows.length)$(id).textContent="No matching records.";
    }
    function render() {
      const params=new URLSearchParams();for(const d of T.dimensions)for(const id of selected[d])params.append(d,id);history.replaceState(null,"",location.pathname+(params.size?"?"+params:""));
      const rs=resources.filter(r=>T.matches(r,selected,index)),ss=software.filter(r=>T.matches(r,selected,index)),js=jobs.filter(r=>T.matches(r,selected,index,false));
      const cat=T.uniqueCatalog([...rs,...ss]);
      $("resource-count").textContent=rs.length.toLocaleString();$("software-count").textContent=ss.length.toLocaleString();$("catalog-count").textContent=cat.length.toLocaleString();$("job-count").textContent=js.length.toLocaleString();
      const dim=$("dimension").value;
      const missing=jobs.filter(r=>!r.sharedTags?.[dim]?.length).length;
      $("status").textContent=`${jobs.length.toLocaleString()} active eligible jobs · ${missing.toLocaleString()} without an accepted ${dim} assignment · vocabulary ${vocab.version}`;
      $("counts").replaceChildren();
      const rows=T.coverageRows(rs,ss,js,index,dim);
      for(const row of rows){const tr=document.createElement("tr"),td=document.createElement("td"),button=document.createElement("button");button.textContent=row.label;button.onclick=()=>{selected[dim]=[row.id];for(const o of $(dim).options)o.selected=o.value===row.id;render();};td.append(button);tr.append(td);for(const key of ["resources","software","catalogEntities","jobs","employers"]){const cell=document.createElement("td");cell.textContent=row[key].toLocaleString();tr.append(cell);}$("counts").append(tr);}
      showRecords("catalog-records",cat);showRecords("job-records",js,true);
    }
    render();
  } catch(error){$("status").textContent=`Comparison unavailable: ${error.message}`;}
})();
