from functools import wraps
from nano import NanoApplication
from jinja2 import Environment, FileSystemLoader

class KlausApplication(NanoApplication):
    def __init__(self, *args, **kwargs):
        super(KlausApplication, self).__init__(*args, **kwargs)
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        self.jinja_env.globals['build_url'] = self.build_url

    def route(self, pattern):
        super_decorator = super(KlausApplication, self).route(pattern)
        def decorator(callback):
            @wraps(callback)
            def wrapper(*args, **kwargs):
                res = callback(*args, **kwargs)
                if isinstance(res, dict):
                    res = self.render_template(callback.__name__ + '.html', **res)
                return res
            return super_decorator(wrapper)
        return decorator

    def render_template(self, **kwargs):
        return self.jinja_env.get_template(template_name).render(**kwargs)

app = KlausApplication(debug=True, default_content_type='text/html')


@app.route('/')
def repo_list(env):
    return {'repos' : app.repos.items()}

@app.route('/:repo:/')
def view_repo(env, repo):
    pass
