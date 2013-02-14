
function readMoreReadme(repository) {
  var preview = repository + "-preview";
  var full = repository + "-full";
  document.getElementById(preview).style.display = 'none';
  document.getElementById(full).style.display = '';
}

function readLessReadme(repository) {
  var preview = repository + "-preview";
  var full = repository + "-full";
  document.getElementById(full).style.display = 'none';
  document.getElementById(preview).style.display = '';
}

