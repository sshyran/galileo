import json
import flask
import parser
import inspect
import re
from flask import Blueprint, render_template, abort
from flask.ext import restful

class Route(object):
    method_order = ['GET', 'POST', 'PUT', 'DELETE']
    def __init__(self, path, resource, methods, arguments):
        self.paths = [ path ]
        self.resource = resource
        self.methods = [ method for method in self.method_order if method in methods]
        self.arguments = arguments

    def add_path(self, path):
        if path not in self.paths:
            self.paths.append(path)

def _parse_argument(arg):
    arg = arg.replace("add_argument",'', 1)
    arg = arg.replace("(", "(name=", 1)
    arg = arg.replace("(", '')
    arg = arg.replace(")", '')
    arg = arg.replace("'", '')
    arg = arg.replace('"', '')
    kwargs = arg.split(",")

    data = {}

    for kwarg in kwargs:
        k,v = kwarg.split("=")
        data[k.strip()] = v.strip()

    return data


label_colors = {
    'GET': 'label-success',
    'POST': 'label-danger',
    'PUT': 'label-warning',
    'DELETE': 'label-info',
}

class Galileo(object):
    def __init__(self, app=None, path=None, **options):

        self.app = app
        self.path = path

        self.blueprint = Blueprint('galileo', __name__,
                                   template_folder='templates',
                                   static_folder='static')
        self.blueprint.add_url_rule("/index", view_func=self.docs, **options)

        self.app.register_blueprint(self.blueprint, url_prefix=self.path)

    def docs(self):
        routes = []
        seen = {}
        for route in self.app.url_map.iter_rules():
            view = self.app.view_functions[route.endpoint]
            if hasattr(view, 'view_class'):
                src_str = inspect.getsource(view.view_class)
                args = {}
                for method in view.methods:
                    method_start = src_str.find(" def {}".format(method.lower()))
                    method_end = src_str.find(" def ", method_start+1)

                    matches = re.findall('add_argument\(.*?\)',
                                         src_str[method_start:method_end], re.S)

                    matches = [ _parse_argument(m) for m in matches ]
                    args[method] = matches

                is_seen = seen.get(view.view_class.__name__)
                if not is_seen:
                    seen[view.view_class.__name__] = Route(
                        route.rule, view.view_class, view.methods, args)
                else:
                    is_seen.add_path(route.rule)

        keys = seen.keys()
        keys.sort()

        routes = [ seen[k] for k in keys ]


        return render_template('index.html', routes=routes,
                               label_colors=label_colors)
