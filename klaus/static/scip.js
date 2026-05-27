/* Hover popover for SCIP occurrences.
 *
 * Reads data-sym / data-display / data-defhref / data-defloc / data-refs
 * attributes emitted by klaus.highlighting and shows a small panel listing
 * the symbol's display name, definition link, and references.
 */
(function () {
  function makePopover() {
    var el = document.createElement('div');
    el.className = 'scip-popover';
    el.style.display = 'none';
    document.body.appendChild(el);
    return el;
  }

  var popover = null;
  var activeTarget = null;
  var hideTimer = null;

  function hide() {
    if (popover) popover.style.display = 'none';
    activeTarget = null;
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, 200);
  }

  function cancelHide() {
    clearTimeout(hideTimer);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function show(target) {
    if (!popover) popover = makePopover();
    cancelHide();
    activeTarget = target;

    var display = target.getAttribute('data-display') || '';
    var defhref = target.getAttribute('data-defhref');
    var defloc = target.getAttribute('data-defloc');
    var refsAttr = target.getAttribute('data-refs');
    var refs = [];
    if (refsAttr) {
      try { refs = JSON.parse(refsAttr); } catch (e) { refs = []; }
    }

    var html = '';
    if (display) {
      html += '<div class="scip-popover-name">' + escapeHtml(display) + '</div>';
    }
    if (defhref) {
      html += '<div class="scip-popover-def">' +
              '<span class="scip-popover-label">definition</span> ' +
              '<a href="' + escapeHtml(defhref) + '">' +
              escapeHtml(defloc || 'definition') + '</a></div>';
    }
    if (refs.length) {
      html += '<div class="scip-popover-refs-header">' +
              refs.length + ' reference' + (refs.length === 1 ? '' : 's') +
              '</div><ul class="scip-popover-refs">';
      var max = 10;
      for (var i = 0; i < Math.min(refs.length, max); i++) {
        var r = refs[i]; // [path, line, href]
        html += '<li><a href="' + escapeHtml(r[2]) + '">' +
                escapeHtml(r[0]) + ':' + r[1] + '</a></li>';
      }
      if (refs.length > max) {
        html += '<li class="scip-popover-more">' +
                (refs.length - max) + ' more&hellip;</li>';
      }
      html += '</ul>';
    }
    if (!html) {
      hide();
      return;
    }
    popover.innerHTML = html;
    popover.style.display = 'block';

    var rect = target.getBoundingClientRect();
    var top = rect.bottom + window.scrollY + 4;
    var left = rect.left + window.scrollX;
    // Keep popover on-screen horizontally
    var maxLeft = window.scrollX + document.documentElement.clientWidth -
                  popover.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, maxLeft);
    popover.style.top = top + 'px';
    popover.style.left = left + 'px';
  }

  document.addEventListener('mouseover', function (e) {
    var target = e.target.closest && e.target.closest('[data-sym]');
    if (target) {
      if (target !== activeTarget) show(target);
      cancelHide();
    } else if (e.target.closest && e.target.closest('.scip-popover')) {
      cancelHide();
    }
  });

  document.addEventListener('mouseout', function (e) {
    if (e.target.closest && (e.target.closest('[data-sym]') ||
        e.target.closest('.scip-popover'))) {
      scheduleHide();
    }
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;
    if (!e.target.closest('[data-sym]') && !e.target.closest('.scip-popover')) {
      hide();
    }
  });
})();
