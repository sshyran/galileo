import json
import flask
import parser
import inspect
import re
from flask import Blueprint, render_template, abort
from flask.ext import restful
import importlib


class Route(object):
    method_order = ['GET', 'POST', 'PUT', 'DELETE']

    def __init__(self, path, resource, methods, arguments, fields, service=None,
                 src_base_url=None, filename=None, line_no=None):
        self.paths = [path]
        self.resource = resource
        self.methods = [
            method for method in self.method_order if method in methods]
        self.arguments = arguments
        self.fields = fields

        self.docstring = inspect.getdoc(resource) or ''
        self.service = service
        self.src_base_url = src_base_url
        self.filename = filename
        self.line_no = line_no

    def add_path(self, path):
        if path not in self.paths:
            self.paths.append(path)

    def method_docs(self, method):
        func = getattr(self.resource, method.lower())
        return inspect.getdoc(func) or ''

    def get_fields(self):
        fields = {}

        for method, field in self.fields.items():
            for name, field_type in field.items():
                if hasattr(field_type, '__name__'):
                    fields[name] = field_type.__name__
                else:
                    fields[name] = field_type.__class__.__name__

        return json.dumps(fields, indent=4)

    def source_url(self):
        return "{}/{}/blob/master/{}#L{}".format(self.src_base_url,
                                                 self.service, self.filename,
                                                 self.line_no)


def _parse_argument(arg):
    arg = arg.replace("add_argument", '', 1)
    arg = arg.replace("(", "(name=", 1)
    arg = arg.replace("(", '')
    arg = arg.replace(")", '')
    arg = arg.replace("'", '')
    arg = arg.replace('"', '')
    kwargs = arg.split(",")

    data = {}

    for kwarg in kwargs:
        k, v = kwarg.split("=")
        data[k.strip()] = v.strip()

    return data


label_colors = {
    'GET': 'label-success',
    'POST': 'label-danger',
    'PUT': 'label-warning',
    'DELETE': 'label-info',
}


class Galileo(object):

    def __init__(self, app=None, path=None, service=None, src_base_url=None, **options):

        self.app = app
        self.path = path
        self.service = service
        self.src_base_url = src_base_url

        self.blueprint = Blueprint('galileo', __name__,
                                   template_folder='templates',
                                   static_folder='static')
        self.blueprint.add_url_rule("/index", view_func=self.docs, **options)

        self.app.register_blueprint(self.blueprint, url_prefix=self.path)

    def _find_arguments(self, source):
        matches = re.findall('add_argument\(.*?\)', source, re.S)
        matches = [_parse_argument(m) for m in matches]
        return matches

    def _find_fields(self, source):
        matches = re.findall('marshal_with\((.*?)\)', source, re.S)
        return matches

    def docs(self):
        routes = []
        seen = {}
        for route in self.app.url_map.iter_rules():
            view = self.app.view_functions[route.endpoint]
            if hasattr(view, 'view_class'):
                src_str = inspect.getsource(view.view_class)
                lines, line_no = inspect.getsourcelines(view.view_class)

                args = {}
                fields = {}

                for method in view.methods:
                    method_start = src_str.find(
                        " def {}".format(method.lower()))
                    method_end = src_str.find(" def ", method_start + 1)

                    args[method] = self._find_arguments(
                        src_str[method_start:method_end])

                    marshal_start = src_str.rfind("marshal", 0, method_start)
                    field_names = self._find_fields(
                        src_str[marshal_start:method_start])

                    mod = importlib.import_module(view.view_class.__module__)
                    filename = mod.__name__.replace(".", "/")
                    if mod.__file__.find("__init__.py") != -1:
                        filename = "{}/__init__.py".format(filename)
                    else:
                        filename = "{}.py".format(filename)

                    for field in field_names:
                        if hasattr(mod, field):
                            fields[method] = getattr(mod, field)

                is_seen = seen.get(view.view_class.__name__)
                if not is_seen:
                    seen[view.view_class.__name__] = Route(
                        route.rule, view.view_class, view.methods, args, fields,
                        self.service, self.src_base_url, filename=filename,
                        line_no=line_no)
                else:
                    is_seen.add_path(route.rule)

        keys = seen.keys()
        keys.sort()

        routes = [seen[k] for k in keys]

        route_nav = {}
        for k, v in seen.items():
            for path in v.paths:
                route_nav[path] = v

        keys = route_nav.keys()
        keys.sort()

        route_nav = [(path, route_nav[path]) for path in keys]

        return render_template('index.html', routes=routes, route_nav=route_nav,
                               label_colors=label_colors)
