
from flask import Flask, render_template, url_for, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import slate3k as slate
import io


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
db = SQLAlchemy(app)
current_user = None
current_admin = None

def get_info_from_pdf(pdf_path):
    
    with open(pdf_path,'rb') as f:
        extracted_text = slate.PDF(f)

    result = {'yazar':[], 'danısman':[], 'juri':[]}

    tmp = ""
    for line in extracted_text[3].lower().split("\n"):
        tmp += line.strip() + ":" if (":" in line) and ("i̇mza" not in line) else ""
    tmp = tmp.split(':')[1::2]
    for i in range(0, len(tmp), 2):
        result["yazar"].append({'ad':tmp[i+1], 'numara':tmp[i]})

    page1 = [i.strip().lower() for i in extracted_text[1].split('\n') if (i != '')]
    
    result['ders ad'] = page1[3]
    result['proje baslik'] = page1[4]

    for i in range(len(page1)):
        if 'danışman' in page1[i]:
            result['danısman'].append(page1[i-1])
            result['juri'].append(page1[i-1])
        if 'jüri' in page1[i]:
            result['juri'].append(page1[i-1])
        if 'tarih' in page1[i]:
            result['tez tarih'] = page1[i].split(':')[1].strip()

    _, rest = extracted_text[10].lower().split('özet', 1)
    özet, anahtar = rest.split('anahtar kelimeler:')
    

    result['ozet'] = "".join(özet)
    result['anahtar'] = list(filter(None, [i.strip() for i in (anahtar.replace('\n', ',').replace('.', ',').split(',')) if(i!='ix')]))
    return result

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<Admin {self.id}> => Email:{self.email},Password{self.password}"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    uploads = db.relationship('Upload', backref='owner')

    def __repr__(self) -> str:
        return f"<User {self.id}> => Email:{self.email},Password{self.password}"


class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pdf_file = db.Column(db.LargeBinary, nullable=False)  # bdf dosya
    author_names = db.Column(db.String(100), nullable=False) # Yazar bilgileri (numara dahil)
    type = db.Column(db.String(30), nullable=False) # Araştırma problemi veya bitirme projesi
    project_summary = db.Column(db.VARCHAR, nullable=False)  # Proje özeti
    submitted_term = db.Column(db.String(200), nullable=False)  # Geönderildiği dönem
    keywords = db.Column(db.VARCHAR, nullable=False)  # Anahtar Kelimeler
    advisors = db.Column(db.String(200))  # Danısman adları
    jury = db.Column(db.String(200))  # Juri adları
    # sql atanma tarihi ( otomatik )
    date_created = db.Column(db.DateTime, default=datetime.utcnow())

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Foregin key

    def __repr__(self) -> str:
        return f"<Upload {self.id}> => Date:{self.date_created}, By:{self.user_id}"


# TODO: User indexden kullanıcı ekle seçenekleri kaldır
# TODO: Veri tabanları

@app.route('/')
def index():
    return redirect("/login", code=302)


@app.route('/login')
def user_login():
    return render_template("user_login.html")

@app.route('/admin/login')
def admin_login():
    return render_template("admin_login.html")


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_post():
    global current_admin
    email = request.form['email']
    password = request.form['password']
    current_admin = Admin.query.filter_by(
        email=email, password=password).first()

    return redirect("/admin/index", 302)


@app.route('/login', methods=['GET', 'POST'])
def user_login_post():
    global current_user    
    email = request.form['email']
    password = request.form['password']
    current_user = User.query.filter_by(email=email, password=password).first()

    return redirect("/index", 302)


@app.route('/index')
def user_index():
    global current_user

    if current_user:
        return render_template("user_index.html")
    else:
        return redirect("/login", 302)

@app.route('/pdf')
def pdf_table_user():
    if current_user:
        return render_template('user_pdf-tables.html', data=Upload.query.filter(Upload.user_id==current_user.id).all(), User=User)
    else:
        return redirect("/login", 302)

@app.route('/index', methods=['GET', 'POST'])
def get_pdf():

    pdf = request.files['pdf-file']
    if pdf.filename != '':
        pdf.save('output.pdf')
    
    info = (get_info_from_pdf('output.pdf'))
    yazar_string = ",".join(["{}:{}:{}".format(i['ad'], i['numara'], "1. Öğretim" if i['numara'].strip()[5] =='1' else "2. Öğretim") for i in info['yazar']])
    
    _, ay, yıl = info['tez tarih'].split('.')
    dönem = "GÜZ" if ay in ['09', '10', '11', '12', '01', '02'] else "BAHAR"
    submitted_term_text = f"{int(yıl)}-{int(yıl)+1} {dönem}"
    
    f = open('output.pdf', 'rb')

    upload = Upload(pdf_file = f.read(),
                    author_names = yazar_string,
                    type = info['ders ad'],
                    project_summary = info['proje baslik'] + "," + info['ozet'],
                    submitted_term = submitted_term_text,
                    keywords = ",".join(info['anahtar']),
                    advisors = ",".join(info['danısman']),
                    jury = ",".join(info['juri']),
                    user_id = current_user.id
                    )

    f.close()
    db.session.add(upload)
    db.session.commit()

    return redirect('/index', 302)

@app.route('/admin/index')
def admin_index():
    global current_admin

    if current_admin:
        return render_template("admin_index.html")
    else:
        return redirect("/admin/login", 302)


@app.route('/signup')
def signup():
    return render_template("user_signup.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup_post():

    email = request.form['email']
    password = request.form['password']
    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()
    return redirect("/login", 302)

@app.route('/admin/pdf')
def pdf_table():
    if current_admin:
        return render_template('admin_pdf-tables.html', data=Upload.query.all(), User=User)
    else:
        return redirect("/admin/login", 302)

@app.route('/admin/new', methods=['POST'])
def new_user():
    email = request.form['email']
    password = request.form['password']
    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()
    return redirect('/admin/index', 302)

@app.route('/admin/del', methods=['POST'])
def del_user():
    email = request.form['email']
    User.query.filter_by(email=email).delete()
    db.session.commit()
    return redirect('/admin/index', 302)

@app.route('/admin/update', methods=['POST'])
def update_user():
    return redirect('/admin/index', 302)   

@app.route('/logout')
def user_logout():
    global current_user
    current_user = None
    return redirect('/login', 302)

@app.route('/admin/logout')
def admin_logout():
    global current_admin
    current_admin = None
    return redirect('/admin/login', 302)

@app.route("/pdf_download", methods=['POST', 'GET'])
def download_pdf():
    id = request.args.get('pdf-id')
    print(id)
    row = Upload.query.filter(Upload.id == id).first()
    print(row.type)
    return send_file(io.BytesIO(row.pdf_file), download_name='download.pdf')

@app.route("/pdf_remove", methods=['POST', 'GET'])
def remove_pdf():
    id = request.args.get('pdf-id')
    print(id)
    Upload.query.filter(Upload.id == id).delete()
    db.session.commit()
    return redirect(request.referrer, 302)

if __name__ == '__main__':
    app.run(debug=True)
