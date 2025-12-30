// Enhanced Toast Notifications (positioning, animations, priority, responsivity)
(function() {
  try {
    var css = [
      ':root{--toast-gap:12px;--toast-radius:4px;--toast-shadow:0 6px 16px rgba(0,0,0,0.12)}',
      '#bf1-toast-container{position:fixed;top:20px;right:20px;left:auto;bottom:auto;display:flex;flex-direction:column;gap:var(--toast-gap);z-index:50;pointer-events:none}',
      '@media(max-width:640px){#bf1-toast-container{top:auto;bottom:20px;right:auto;left:50%;transform:translateX(-50%)}}',
      '@keyframes bf1-toast-fade-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}',
      '@keyframes bf1-toast-fade-out{from{opacity:1}to{opacity:0}}',
      '.bf1-toast-enter{animation:bf1-toast-fade-in 220ms ease-out both}',
      '.bf1-toast-exit{animation:bf1-toast-fade-out 220ms ease-in both}',
      '.bf1-toast{border-radius:var(--toast-radius);box-shadow:var(--toast-shadow);padding:10px 12px;display:flex;align-items:start;gap:10px;max-width:360px;width:calc(100vw - 40px);pointer-events:auto}',
      '@media(max-width:640px){.bf1-toast{max-width:92vw;font-size:.92rem}}',
      '@media(min-width:1024px){.bf1-toast{font-size:1rem}}',
      '.bf1-toast .bf1-toast-close{margin-left:8px;opacity:.8}',
      '.bf1-toast .bf1-toast-close:hover{opacity:1}'
    ].join('');
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  } catch(e) {}

  var container = document.getElementById('bf1-toast-container') || (function(){
    var el = document.createElement('div'); el.id = 'bf1-toast-container'; document.body.appendChild(el); return el;
  })();

  var MAX_TOASTS = 3;
  var TYPE_ICON = { info: 'fa-info-circle', success: 'fa-check-circle', warning: 'fa-exclamation-triangle', error: 'fa-exclamation-circle' };
  var TYPE_STYLE = {
    info: 'bg-blue-600 text-white',
    success: 'bg-green-600 text-white',
    warning: 'bg-yellow-500 text-black',
    error: 'bg-red-600 text-white'
  };
  var TYPE_PRIORITY = { info: 0, success: 1, warning: 2, error: 3 };

  function anchorContainer() {
    try {
      var nav = document.querySelector('nav');
      var rect = nav ? nav.getBoundingClientRect() : null;
      var isMobile = window.matchMedia('(max-width: 640px)').matches;
      if (isMobile) {
        container.style.top = 'auto';
        container.style.bottom = '20px';
        container.style.left = '50%';
        container.style.right = 'auto';
        container.style.transform = 'translateX(-50%)';
      } else {
        var topOffset = rect ? Math.max(20, Math.floor(rect.bottom) + 20) : 20;
        container.style.top = topOffset + 'px';
        container.style.bottom = 'auto';
        container.style.right = '20px';
        container.style.left = 'auto';
        container.style.transform = 'none';
      }
    } catch (e) {}
  }
  window.addEventListener('resize', anchorContainer);
  window.addEventListener('load', anchorContainer);
  anchorContainer();

  function removeToast(el) {
    try { el.classList.add('bf1-toast-exit'); setTimeout(function(){ el && el.parentElement && el.parentElement.remove(); }, 220); } catch (e) {}
  }

  function clampToasts() {
    var items = Array.prototype.slice.call(container.children).map(function(el){
      var toast = el.querySelector('.bf1-toast');
      return { el: el, pr: Number(toast && toast.getAttribute('data-priority') || 0), ts: Number(toast && toast.getAttribute('data-ts') || 0) };
    });
    while (items.length > MAX_TOASTS) {
      items.sort(function(a,b){ return (a.pr - b.pr) || (a.ts - b.ts); });
      var victim = items.shift();
      if (victim && victim.el) removeToast(victim.el.querySelector('.bf1-toast'));
    }
  }

  function showToast(opts) {
    opts = opts || {};
    var title = opts.title || '';
    var message = opts.message || '';
    var type = ['info','success','warning','error'].indexOf(opts.type) >= 0 ? opts.type : 'info';
    var priority = typeof opts.priority === 'number' ? opts.priority : TYPE_PRIORITY[type];
    var duration = Math.min(Math.max((opts.duration || 4000), 3000), 5000);
    var dismissible = opts.dismissible !== false;

    var wrapper = document.createElement('div');
    var toast = document.createElement('div');
    wrapper.className = 'pointer-events-auto bf1-toast-enter';
    toast.className = TYPE_STYLE[type] + ' bf1-toast ring-1 ring-white/20';
    toast.setAttribute('role', (type === 'error' || type === 'warning') ? 'alert' : 'status');
    toast.setAttribute('aria-live', (type === 'error' || type === 'warning') ? 'assertive' : 'polite');
    toast.setAttribute('aria-atomic', 'true');
    toast.setAttribute('data-priority', String(priority));
    toast.setAttribute('data-ts', String(Date.now()));

    var icon = document.createElement('i'); icon.className = 'fas ' + TYPE_ICON[type] + ' text-xl flex-shrink-0';
    var content = document.createElement('div'); content.className = 'flex-1';
    if (title) { var h = document.createElement('div'); h.className = 'font-semibold'; h.textContent = title; content.appendChild(h); }
    var msg = document.createElement('div'); msg.className = 'text-sm'; msg.textContent = message; content.appendChild(msg);

    var closeBtn = null;
    if (dismissible) { closeBtn = document.createElement('button'); closeBtn.className = 'bf1-toast-close focus:outline-none'; closeBtn.setAttribute('aria-label','Fermer la notification'); closeBtn.innerHTML = '<i class="fas fa-times"></i>'; }

    toast.appendChild(icon); toast.appendChild(content); if (closeBtn) toast.appendChild(closeBtn);
    wrapper.appendChild(toast); container.appendChild(wrapper);

    clampToasts();

    var timer = null;
    function dismiss(){ if (timer) { clearTimeout(timer); timer = null; } removeToast(toast); }
    if (dismissible && closeBtn) { closeBtn.addEventListener('click', dismiss); }
    timer = setTimeout(dismiss, duration);
  }

  // Public API
  window.showToast = showToast;
})();