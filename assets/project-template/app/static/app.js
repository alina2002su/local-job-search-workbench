document.addEventListener('DOMContentLoaded',()=>{
  const scrollKey=`workbench-scroll:${location.pathname}`;
  const savedScroll=sessionStorage.getItem(scrollKey);
  if(savedScroll!==null){
    sessionStorage.removeItem(scrollKey);
    requestAnimationFrame(()=>requestAnimationFrame(()=>window.scrollTo(0,Number(savedScroll)||0)));
  }

  const today=document.querySelector('[data-today]');
  if(today)today.textContent=new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'long'}).format(new Date());
  document.querySelectorAll('tr[data-href]').forEach(row=>row.addEventListener('click',event=>{if(!event.target.closest('a,button,input,select,textarea,label,form'))location.href=row.dataset.href}));
  document.querySelectorAll('[data-toggle]').forEach(button=>button.addEventListener('click',()=>document.querySelector(button.dataset.toggle)?.classList.toggle('hidden')));
  document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{
    const element=document.querySelector(button.dataset.copy);
    await navigator.clipboard.writeText(element.value||element.textContent);
    const old=button.textContent;button.textContent='已复制';setTimeout(()=>button.textContent=old,1400);
  }));

  document.querySelectorAll('[data-todo-row]').forEach(row=>{
    const closeOthers=()=>document.querySelectorAll('[data-todo-row].delete-open').forEach(other=>{if(other!==row)other.classList.remove('delete-open')});
    row.querySelector('[data-todo-menu]')?.addEventListener('click',()=>{closeOthers();row.classList.toggle('delete-open')});
    row.addEventListener('contextmenu',event=>{event.preventDefault();closeOthers();row.classList.add('delete-open')});
    let startX=0,startY=0;
    row.addEventListener('touchstart',event=>{startX=event.touches[0].clientX;startY=event.touches[0].clientY},{passive:true});
    row.addEventListener('touchend',event=>{
      const dx=event.changedTouches[0].clientX-startX,dy=event.changedTouches[0].clientY-startY;
      if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)){closeOthers();row.classList.toggle('delete-open',dx<0)}
    },{passive:true});
  });
  document.querySelectorAll('[data-pool-row]').forEach(row=>{
    const closeOthers=()=>document.querySelectorAll('[data-pool-row].delete-open').forEach(other=>{if(other!==row)other.classList.remove('delete-open')});
    row.querySelector('[data-pool-menu]')?.addEventListener('click',event=>{event.stopPropagation();closeOthers();row.classList.toggle('delete-open')});
    row.addEventListener('contextmenu',event=>{event.preventDefault();closeOthers();row.classList.add('delete-open')});
    let startX=0,startY=0;
    row.addEventListener('touchstart',event=>{startX=event.touches[0].clientX;startY=event.touches[0].clientY},{passive:true});
    row.addEventListener('touchend',event=>{
      const dx=event.changedTouches[0].clientX-startX,dy=event.changedTouches[0].clientY-startY;
      if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)){closeOthers();row.classList.toggle('delete-open',dx<0)}
    },{passive:true});
  });
  document.addEventListener('click',event=>{
    if(!event.target.closest('[data-todo-row]'))document.querySelectorAll('[data-todo-row].delete-open').forEach(row=>row.classList.remove('delete-open'));
  });
  document.querySelectorAll('[data-confirm-delete]').forEach(form=>form.addEventListener('submit',event=>{
    if(!confirm(form.dataset.confirmDelete||'确定删除这条待办吗？删除后无法恢复。'))event.preventDefault();
  }));
  document.querySelectorAll('form[data-preserve-scroll]').forEach(form=>form.addEventListener('submit',event=>{
    if(!event.defaultPrevented)sessionStorage.setItem(scrollKey,String(window.scrollY));
  }));
  document.querySelectorAll('[data-auto-submit]').forEach(control=>control.addEventListener('change',()=>control.form?.requestSubmit()));

  document.querySelectorAll('.sortable-table').forEach(table=>{
    const body=table.tBodies[0],buttons=[...table.querySelectorAll('.table-sort')];
    if(!body||!buttons.length)return;
    const sortKey=`workbench-sort:${location.pathname}`;
    const collator=new Intl.Collator('zh-CN',{numeric:true,sensitivity:'base'});
    const stageOrder=['已投递','测评','笔试','群面','一面','二面','三面','终面','HR面','Offer','人才库','未通过','主动放弃'];
    const urgencyOrder={missing:0,relaxed:1,normal:2,high:3,urgent:4,overdue:5};
    const cellValue=(row,index)=>{
      const cell=row.cells[index];
      if(!cell)return '';
      const control=cell.querySelector('input,select');
      return String(control?.value??cell.dataset.sortValue??cell.textContent??'').trim();
    };
    const comparable=(value,type)=>{
      if(type==='date')return Date.parse(value)||0;
      if(type==='stage')return stageOrder.indexOf(value)+1;
      if(type==='urgency')return urgencyOrder[value]??0;
      return value;
    };
    const applySort=(index,type,dir,remember=true)=>{
      const rows=[...body.rows].map((row,originalIndex)=>({row,originalIndex,value:cellValue(row,index)}));
      rows.sort((a,b)=>{
        if(!a.value&&!b.value)return a.originalIndex-b.originalIndex;
        if(!a.value)return 1;
        if(!b.value)return -1;
        const av=comparable(a.value,type),bv=comparable(b.value,type);
        const result=type==='text'?collator.compare(av,bv):(av-bv);
        return (result||a.originalIndex-b.originalIndex)*(dir==='asc'?1:-1);
      });
      rows.forEach(item=>body.appendChild(item.row));
      buttons.forEach(button=>{
        const active=Number(button.dataset.sortIndex)===index;
        button.classList.toggle('active',active);
        button.closest('th')?.setAttribute('aria-sort',active?(dir==='asc'?'ascending':'descending'):'none');
        const icon=button.querySelector('span');if(icon)icon.textContent=active?(dir==='asc'?'↑':'↓'):'↕';
      });
      table.dataset.sortIndex=String(index);table.dataset.sortDir=dir;
      if(remember)sessionStorage.setItem(sortKey,JSON.stringify({index,type,dir}));
    };
    buttons.forEach(button=>button.addEventListener('click',event=>{
      event.preventDefault();
      const index=Number(button.dataset.sortIndex),type=button.dataset.sortType||'text';
      const same=Number(table.dataset.sortIndex)===index;
      const dir=same?(table.dataset.sortDir==='asc'?'desc':'asc'):(button.dataset.defaultDir||'asc');
      applySort(index,type,dir);
    }));
    try{
      const saved=JSON.parse(sessionStorage.getItem(sortKey)||'null');
      if(saved&&buttons.some(button=>Number(button.dataset.sortIndex)===saved.index))applySort(saved.index,saved.type,saved.dir,false);
    }catch(_){sessionStorage.removeItem(sortKey)}
  });
});
