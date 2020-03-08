from flask import Flask, flash
from datetime import datetime
from flask import Flask, jsonify, redirect, url_for
from flask import request
from flask import render_template
from urllib.parse import quote
from flask_sqlalchemy import SQLAlchemy
from ddns import config
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField,SelectField,IntegerField
from wtforms.validators import DataRequired,AnyOf
from wtforms.compat import text_type
import string

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{config.db_path}/{config.db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #禁止py3报兼容性问题
app.config['SECRET_KEY'] = 'any secret string'
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


class SelectInputField(SelectField):

    def __init__(self, label=None, validators=None, coerce=text_type, choices=None, **kwargs):
        super(SelectInputField, self).__init__(label, validators, coerce, choices, **kwargs)

    def pre_validate(self, form):
        pass


class RecordForm(FlaskForm):
    record_name=SelectInputField("record_name", validators=[DataRequired()], choices=[("abc","<span class='v_title'>abc</span><span class='v_tip'>二级域名abc.example.com</span>"),
                                                    ("@", '<span class="v_title">@</span><span class="v_tip">直接解析example.com</span>'),
                                                    ("*", '<span class="v_title">*</span><span class="v_tip">泛解析*.example.com</span>')], **{"id":'record_name'})
    ttl = SelectField("ttl", validators=[DataRequired()], choices=[("60", "1分钟"), ("300", "5分钟"), ("900", "15分钟"), ("1800", "30分钟"), ("3600", "60分钟")], **{"id": 'ttl'})
    record_class=StringField("record_class", validators=[AnyOf(values=["IN"]),DataRequired()], default="IN",  **{"id":'record_class'})
    record_type = SelectField("record_type", validators=[AnyOf(values=["A","AAAA","CNAME","MX","TXT","NS"]),DataRequired()], choices=[("A", "A"), ("AAAA", "AAAA"), ("CNAME", "CNAME"), ("MX", "MX"), ("TXT", "TXT"),("NS", "NS")], **{"id": 'record_type'})
    record_value=StringField("record_value", validators=[DataRequired()],  **{"id":'record_value'})
    comment=StringField("comment",  **{"id":'comment'})
    flag = SelectField("flag", validators=[AnyOf(values=["DEFAULT","DDNS"]), DataRequired()], choices=[("DEFAULT", "默认"), ("DDNS", "动态DNS")], **{"id": 'flag'})
    is_enable = SelectField("is_enable",  validators=[AnyOf(values=["Y","N"]), DataRequired()], choices=[("Y", "是"), ("N", "否")], **{"id": 'is_enable'})

    domain_name = StringField("domain_name", validators=[DataRequired()], **{"id": 'domain_name'})
    id = StringField("id", **{"id": 'id'})
    user = StringField("user", **{"id": 'user'})

    def to_record(self):
        record = Records()
        record.id = None if self.data['id']=='' else self.data['id']
        record.domain_name = self.data['domain_name']
        record.name = self.data['record_name']
        record.ttl = self.data['ttl']
        record.record_class = self.data['record_class']
        record.record_type = self.data['record_type']
        record.record_data = self.data['record_value']
        record.last_modify = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record.comment = self.data.get("comment")
        record.flag = self.data['flag']
        record.enable = self.data['is_enable']
        record.user = self.data.get("user")
        return record

    def get_errors(self):
        errors = ''
        for field, msg in self.errors.items():
            errors += f"{field}:{msg}\n"
        return errors


class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String, unique=True, nullable=False)


class Records(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String, unique=False, nullable=False)
    name = db.Column(db.String, unique=False, nullable=False)
    ttl = db.Column(db.Integer, unique=False, nullable=False)
    record_class = db.Column(db.String, default="IN", unique=False, nullable=False)
    record_type = db.Column(db.String, unique=False, nullable=False)
    record_data = db.Column(db.String, unique=False, nullable=False)
    last_modify = db.Column(db.String, unique=False, nullable=False)
    comment = db.Column(db.String, unique=False, nullable=True)
    flag = db.Column(db.String, unique=False, nullable=True)
    enable = db.Column(db.String, unique=False, nullable=False)
    user = db.Column(db.String, default='admin', unique=False, nullable=False)

    def merge(self, record):
        self.domain_name = record.domain_name
        self.name = record.name
        self.ttl = record.ttl
        self.record_class = record.record_class
        self.record_type = record.record_type
        self.record_data = record.record_data
        self.last_modify = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.comment = record.comment
        self.flag = record.flag
        self.enable = record.enable
        self.user = "admin" if record.user is None else record.user


db.create_all()
db.session.commit()


@app.route('/')
@app.route('/<path:domain_name>')
@app.route('/<path:domain_name>/<int:record_id>')
@auth.login_required
def index(domain_name=None, record_id=None):
    if domain_name:
        records = Records.query.filter_by(domain_name=domain_name).all()
    else:
        records = []

    domains = Domain.query.all()
    if record_id is not None:
        r = Records.query.get(record_id)
    else:
        r = Records()
    return render_template("index.html", **{"records":records, "domains":domains, "cur_domain":domain_name, 'form':RecordForm(), "record_id":record_id, "r":r})


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
    form = RecordForm()
    domain_name = request.form.get('domain_name')
    if form.validate_on_submit():
        record = form.to_record()
        try:
            if record.id: # update
                r = Records.query.filter_by(id=record.id).first()
                r.merge(record)
                db.session.merge(r)
                db.session.commit()
            else:
                db.session.add(record)
                db.session.commit()
        except Exception as e:
            flash(str(e))
        else:
            flash("成功")
    else:
        flash(form.get_errors())

    return redirect(f"/{domain_name}")


@app.route('/delete-record/<int:record_id>/<path:domain_name>', methods=['GET'])
def delete_record(record_id, domain_name):
    Records.query.filter_by(id=record_id).delete()
    db.session.commit()
    return redirect(f"/{domain_name}")


@app.route('/enable/<int:record_id>/<path:domain_name>/<enable>', methods=['GET'])
def enable(record_id, domain_name, enable):
    r = Records.query.get(record_id)
    r.enable = enable
    db.session.commit()
    return redirect(f"/{domain_name}")


@app.route('/edit-record/<int:record_id>/<path:domain_name>', methods=['GET'])
def edit_record(record_id, domain_name):
    return redirect(f"/{domain_name}/{record_id}")


if __name__ == '__main__':
    app.run()
