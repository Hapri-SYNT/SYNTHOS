# DNA Dojo API - Vulnerable by Design
from flask import Flask, request, jsonify, render_template_string
import subprocess, pickle, jwt, sqlite3, time, os, yaml
import xml.etree.ElementTree as ET

app = Flask(__name__)
db = sqlite3.connect(':memory:', check_same_thread=False)
db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, balance REAL, role TEXT)")
db.execute("INSERT INTO users VALUES (1,'admin','admin123',1000000.0,'admin')")
db.execute("INSERT INTO users VALUES (2,'user','password',100.0,'user')")
db.commit()

@app.route('/api/user/<int:user_id>')
def get_user(user_id):
    q = f"SELECT username FROM users WHERE id = {user_id}"
    try:
        row = db.execute(q).fetchone()
        return jsonify({"username": row[0]}) if row else ("Not found", 404)
    except: return ("Error", 500)

@app.route('/api/ping')
def ping():
    host = request.args.get('host','localhost')
    return f"<pre>{subprocess.getoutput('ping -c 1 ' + host)}</pre>"

@app.route('/greet')
def greet():
    name = request.args.get('name','World')
    return render_template_string(f"<h1>Hello {name}!</h1>")

@app.route('/api/load', methods=['POST'])
def load_data():
    obj = pickle.loads(request.get_data())
    return jsonify({"result": str(obj)[:200]})

@app.route('/download')
def download():
    with open(request.args.get('file',''), 'r') as f:
        return f"<pre>{f.read()}</pre>"

@app.route('/api/admin')
def admin():
    token = request.headers.get('Authorization','').replace('Bearer ','')
    try:
        p = jwt.decode(token, options={"verify_signature": False})
        if p.get('role') == 'admin': return jsonify({"flag": "CTF{jwt_bypass}"})
    except: pass
    return ("Unauthorized", 403)

@app.route('/api/fetch')
def fetch():
    import urllib.request
    return urllib.request.urlopen(request.args.get('url','http://localhost')).read()[:1000]

@app.route('/api/xml', methods=['POST'])
def parse_xml():
    tree = ET.fromstring(request.get_data())
    return jsonify({c.tag: c.text for c in tree})

@app.route('/api/transfer', methods=['POST'])
def transfer():
    d = request.get_json() or {}
    bal = db.execute(f"SELECT balance FROM users WHERE id={d.get('from',1)}").fetchone()[0]
    if bal >= d.get('amount',0):
        time.sleep(0.1)
        db.execute(f"UPDATE users SET balance=balance-{d['amount']} WHERE id={d['from']}")
        db.execute(f"UPDATE users SET balance=balance+{d['amount']} WHERE id={d['to']}")
        db.commit()
        return jsonify({"status":"sent"})
    return jsonify({"status":"insufficient"})

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files['file']
    f.save(os.path.join('/tmp', f.filename))
    return f"Uploaded: {f.filename}"

@app.route('/api/config', methods=['POST'])
def config():
    return jsonify(yaml.load(request.get_data(), Loader=yaml.Loader))

@app.route('/api/invoice/<int:iid>')
def invoice(iid):
    return jsonify({"invoice_id": iid, "amount": 1000})

@app.route('/api/users', methods=['POST'])
def create_user():
    d = request.get_json() or {}
    db.execute("INSERT INTO users (username,password,balance,role) VALUES (?,?,?,?)",
        (d.get('username'), d.get('password'), d.get('balance',0), d.get('role','user')))
    db.commit()
    return jsonify({"status":"created","role":d.get('role','user')})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
