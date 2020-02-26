from flask import Flask
from flask import Flask, jsonify, redirect, url_for
from flask import request
from flask import render_template
from urllib.parse import quote
from flask_sqlalchemy import SQLAlchemy
from ddns import config
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{config.db_path}/{config.db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #禁止py3报兼容性问题
db = SQLAlchemy(app)
auth = HTTPBasicAuth()
users = {
    config.ui_user: generate_password_hash(config.ui_passwd),
}


@auth.verify_password
def verify_password(username, password):
    if username in users:
        return check_password_hash(users.get(username), password)
    return False


class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String, unique=True, nullable=False)


class Records(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, unique=True, nullable=False)
    ttl = db.Column(db.Integer, unique=False, nullable=False)
    record_class = db.Column(db.String, unique=False, nullable=False)
    record_type = db.Column(db.String, unique=False, nullable=False)
    record_data = db.Column(db.String, unique=False, nullable=False)
    last_modify = db.Column(db.Integer, unique=False, nullable=False)
    comment = db.Column(db.String, unique=False, nullable=True)
    flag = db.Column(db.String, unique=False, nullable=True)
    enable = db.Column(db.String, unique=False, nullable=False)


db.create_all()
db.session.commit()


@app.route('/')
@app.route('/<domain_name>')
@auth.login_required
def index(domain_name=None):
    if domain_name:
        records = Records.query.filter_by(domain_name=domain_name).all()
    else:
        records = Records.query.all()

    domains = Domain.query.all()
    return render_template("index.html", **{"records":records, "domains":domains, "cur_domain":domain_name})


@app.route('/add-domain', methods=['POST'])
def add_domain():
    domain_name=request.form.get("domain_name", default=None)
    if domain_name:
        domain = Domain(domain_name=domain_name)
        db.session.add(domain)
        db.session.commit()
        return redirect(f"/{domain_name}")
    return redirect("/")


@app.route('/add-record', methods=['POST'])
def add_record():
    domain_name = request.form.get('domain_name')
    return redirect(f"/{domain_name}")


if __name__ == '__main__':
    app.run()
