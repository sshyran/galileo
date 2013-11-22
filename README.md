Installing
----------

Add the following to your requirements.txt

```
-e git+git@github.com:Runscope/galileo.git#egg=galileo
```

Usage
-----

Here's an example of basic usage

```python
from flask import Flask
from galileo import Galileo

app = Flask(__name__)

# wrap the flask app and give a url
Galileo(app, "/docs")

```

