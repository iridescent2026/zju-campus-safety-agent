export function brandImage(){const img=new Image();img.src='assets/brand-eye.svg?v=50';img.alt='智安校园 · 原版机械字标识';img.className='ws-brand-image';img.width=760;img.height=190;return img;}
function apply(){for(const link of document.querySelectorAll('.blackgold-workspace .brand-lockup')){link.replaceChildren(brandImage());link.setAttribute('aria-label','智安校园首页');}for(const stage of document.querySelectorAll('.login-stage,.home-stage')){let cover=stage.querySelector('.brand-overlay');if(!cover){cover=document.createElement('a');cover.className='brand-overlay';cover.href='./home.html';cover.setAttribute('aria-label','智安校园');stage.append(cover);}cover.replaceChildren(brandImage());}}

apply();window.addEventListener('workspace-brand-ready',apply);
