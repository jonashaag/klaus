
function showReadme(repository) {
  var button = "readme-button-" + repository;
  var readme = repository + "-readme";
  document.getElementById(button).style.display = 'none';
  document.getElementById(readme).style.display = '';
}

function hideReadme(repository) {
  var button = "readme-button-" + repository;
  var readme = repository + "-readme";
  document.getElementById(readme).style.display = 'none';
  document.getElementById(button).style.display = '';
}

