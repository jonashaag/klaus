from klaus import Klaus

repos = [
    "./repositories/moon-landing.git",
    "./repositories/transformers.git",
]

app = Klaus(repos, "hf-next", use_smarthttp=False)
app.run(debug=True)
