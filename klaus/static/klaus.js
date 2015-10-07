var forEach = function(collection, func) {
  for(var i = 0; i < collection.length; ++i) {
    func(collection[i]);
  }
}


/* General collapse/expand/toggle framework. Used for hiding diffs in commits */
var toggler = {
  expand: function(elem) {
    elem.className = elem.className.replace("collapsed", "");
  },
  collapse: function(elem) {
    if (!/collapsed/.test(elem.className)) {
      elem.className += " collapsed";
    }
  },
  collapseAll: function(selector) {
    forEach(document.querySelectorAll(selector), toggler.collapse);
  },
  expandAll: function(selector) {
    forEach(document.querySelectorAll(selector), toggler.expand);
  }
};


/* Line highlighting logic for diffs */
var highlight_linenos = function(opts) {
  var links = document.querySelectorAll(opts.linksSelector),
      currentHash = location.hash;

  forEach(links, function(a) {
    var lineno = a.getAttribute('href').substr(1),
        associatedLine = document.getElementById(lineno);

    var highlight = function() {
      a.className = 'highlight-line';
      associatedLine.className = 'highlight-line';
      currentHighlight = a;
    }

    var unhighlight = function() {
      if (a.getAttribute('href') != location.hash) {
        a.className = '';
        associatedLine.className = '';
      }
    }

    a.onmouseover = associatedLine.onmouseover = highlight;
    a.onmouseout  = associatedLine.onmouseout  = unhighlight;

    // Initial highlight
    if (a.getAttribute('href') == location.hash) {
      highlight();
    }
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
