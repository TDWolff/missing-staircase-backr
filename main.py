import threading
import subprocess
from flask import render_template, request, make_response
from flask.cli import AppGroup
from flask import Flask, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
import os
import dotenv
from flask_caching import Cache
import redis

dotenv.load_dotenv()


from datetime import datetime
app = Flask(__name__)

# Inject current year into all templates

# Inject current year and current endpoint into all templates
from flask import request
@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.now().year,
        'current_endpoint': request.endpoint
    }

@app.route('/')
def home():
    return render_template('home.html')

# 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

custom_cli = AppGroup('custom', help='Custom commands')
app.cli.add_command(custom_cli)

if __name__ == "__main__":
    is_production = os.getenv('FLASK_ENV') == 'production'
    app.run(
        debug=not is_production,
        host="0.0.0.0",
        port="8087",
        threaded=True
    )