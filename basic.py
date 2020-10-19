from klaus import Klaus

repos = [
    "./repositories/huggingface/moon-landing.git",
    "./repositories/transformers.git",
]

app = Klaus(repos, "klaus.py", use_smarthttp=False)
app.run(debug=True)
