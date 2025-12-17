from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'cle_secrete_scolarite_2025_finale'

# --- MODIFICATION MAJEURE ICI ---
# On définit un chemin absolu pour SQLite afin d'éviter l'erreur "no such table" sur Render
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ecole_v3.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODÈLES DE DONNÉES
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    notes = db.relationship('Note', backref='etudiant', lazy=True)

class Matiere(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_matiere = db.Column(db.String(100), nullable=False)
    nom_professeur = db.Column(db.String(100))
    coefficient = db.Column(db.Integer, default=1)
    notes = db.relationship('Note', backref='matiere', lazy=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_obtenue = db.Column(db.Float, nullable=False)
    session = db.Column(db.String(50))
    requete_erreur = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow) 
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'), nullable=False)

# ==========================================
# SÉCURITÉ
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Accès réservé à l'administration.", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# ROUTES (Inchangées car correctes)
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(matricule=request.form.get('matricule'), is_admin=False).first()
        if user and user.password_hash == request.form.get('password'):
            session['user_id'] = user.id
            session['is_admin'] = False
            return redirect(url_for('dashboard'))
        flash("Identifiants incorrects.", "danger")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    notes = Note.query.filter_by(user_id=user.id).all()
    
    total_points = 0
    total_coefs = 0
    for n in notes:
        total_points += (n.note_obtenue * n.matiere.coefficient)
        total_coefs += n.matiere.coefficient
    
    moyenne = total_points / total_coefs if total_coefs > 0 else 0
    return render_template('dashboard.html', notes=notes, moyenne=moyenne, user=user)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = User.query.filter_by(matricule=request.form.get('matricule'), is_admin=True).first()
        if user and user.password_hash == request.form.get('password'):
            session['user_id'] = user.id
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Identifiants admin incorrects.", "danger")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    requetes = Note.query.filter(Note.requete_erreur != None).order_by(Note.date_creation.desc()).all()
    etudiants = User.query.filter_by(is_admin=False).order_by(User.nom.asc()).all()
    return render_template('admin_dashboard.html', notes_avec_requetes=requetes, etudiants=etudiants)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- CONFIGURATION DE LANCEMENT CORRIGÉE ---
if __name__ == '__main__':
    with app.app_context():
        # Force la création des tables au démarrage
        db.create_all() 
        
        # Création de l'admin par défaut s'il n'existe pas
        if not User.query.filter_by(matricule='ADM01').first():
            adm = User(nom="Direction", matricule="ADM01", password_hash="admin123", is_admin=True)
            db.session.add(adm)
            db.session.commit()
            
    # Configuration spécifique pour Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
