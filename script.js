const menu=document.querySelector('.menu-button');
const nav=document.querySelector('.nav');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')==='true';menu.setAttribute('aria-expanded',String(!open));nav?.classList.toggle('mobile-open',!open)});
const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('revealed')}),{threshold:.12});
document.querySelectorAll('.capability,.step,.security-list>div').forEach(el=>{el.style.transition='opacity .6s ease, transform .6s ease';el.style.opacity='0';el.style.transform='translateY(14px)';observer.observe(el)});
document.addEventListener('scroll',()=>document.querySelectorAll('.revealed').forEach(el=>{el.style.opacity='1';el.style.transform='translateY(0)'}),{passive:true});
