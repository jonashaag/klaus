var highlight_linenos = function(opts) {
  var forEach = function(collection, func) {
    for(var i = 0; i < collection.length; ++i) {
      func(collection[i]);
    }
  }


  var links = document.querySelectorAll(opts.linksSelector);
      currentHash = location.hash;

  forEach(links, function(a) {
    var lineno = a.getAttribute('href').substr(1),
        selector = 'a[name="' + lineno + '"]',
        anchor = document.querySelector(selector),
        associatedLine = opts.getLineFromAnchor(anchor);

    var highlight = function() {
      a.className = 'highlight-line';
      associatedLine.className = 'line highlight-line';
      currentHighlight = a;
    }

    var unhighlight = function() {
      if (a.getAttribute('href') != location.hash) {
        a.className = '';
        associatedLine.className = 'line';
      }
    }

    a.onmouseover = associatedLine.onmouseover = highlight;
    a.onmouseout  = associatedLine.onmouseout  = unhighlight;
  });

 
  window.onpopstate = function() {
    if (currentHash) {
      forEach(document.querySelectorAll('a[href="' + currentHash + '"]'),
              function(e) { e.onmouseout() })
    }
    if (location.hash) {
      forEach(document.querySelectorAll('a[href="' + location.hash + '"]'),
              function(e) { e.onmouseover() });
      currentHash = location.hash;
    }
  };
}
