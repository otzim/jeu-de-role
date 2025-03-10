from flask import Flask, request, redirect, url_for, render_template, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import sqlite3
import os

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

app = Flask(__name__)
app.secret_key = 'une_clé_secrète_très_sécurisée'  # Clé secrète pour les sessions

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Dictionnaire des utilisateurs (à remplacer par une base de données)
users = {
    "admin": os.getenv('WEB_PASSWORD', 'password')  # Nom d'utilisateur et mot de passe
}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Route pour la page de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('characters'))  # Rediriger vers la page des personnages après la connexion
        return "Identifiants invalides", 401
    return render_template('login.html')

# Route pour la déconnexion
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Route pour la page d'accueil
@app.route('/')
def index():
    return "Bienvenue sur la page d'accueil"

# Connexion à la base de données
def get_db_connection():
    conn = sqlite3.connect('rpg_bot.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
    return conn

# Initialisation de la base de données
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            race TEXT,
            class TEXT,
            level INTEGER,
            xp INTEGER,
            hp INTEGER,
            strength INTEGER,
            dexterity INTEGER,
            constitution INTEGER,
            intelligence INTEGER,
            wisdom INTEGER,
            charisma INTEGER,
            invisible_until INTEGER,
            last_spell_used INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Appeler init_db() au démarrage de l'application
init_db()

# Route pour afficher les personnages
@app.route('/characters')
@login_required
def characters():
    print(f"Utilisateur connecté : {current_user.id}")
    return render_template('characters.html')

# Route API pour récupérer les personnages au format JSON
@app.route('/api/characters', methods=['GET'])
def get_characters():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM characters')
    characters = cursor.fetchall()
    conn.close()

    # Convertir les données en une liste de dictionnaires
    characters_list = []
    for character in characters:
        characters_list.append({
            "id": character[0],
            "name": character[1],
            "race": character[2],
            "class": character[3],
            "level": character[4],
            "xp": character[5],
            "hp": character[6],
            "strength": character[7],
            "dexterity": character[8],
            "constitution": character[9],
            "intelligence": character[10],
            "wisdom": character[11],
            "charisma": character[12],
            "invisible_until": character[13],
            "last_spell_used": character[14]
        })
    
    return jsonify(characters_list)

# Route pour créer un personnage
@app.route('/create_character', methods=['GET', 'POST'])
@login_required
def create_character():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))  # Rediriger vers la page de connexion si l'utilisateur n'est pas connecté

    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.form.get('name')
        race = request.form.get('race')
        character_class = request.form.get('class')
        level = request.form.get('level', '1')  # Niveau par défaut à 1
        hp = request.form.get('hp')
        strength = request.form.get('strength')
        dexterity = request.form.get('dexterity')
        constitution = request.form.get('constitution')
        intelligence = request.form.get('intelligence')
        wisdom = request.form.get('wisdom')
        charisma = request.form.get('charisma')

        # Vérifier que tous les champs sont remplis
        if not all([name, race, character_class, level, hp, strength, dexterity, constitution, intelligence, wisdom, charisma]):
            return "Tous les champs sont obligatoires", 400

        # Convertir les valeurs en entiers
        try:
            level = int(level)
            hp = int(hp)
            strength = int(strength)
            dexterity = int(dexterity)
            constitution = int(constitution)
            intelligence = int(intelligence)
            wisdom = int(wisdom)
            charisma = int(charisma)
        except ValueError:
            return "Les caractéristiques doivent être des nombres valides", 400

        # Sauvegarder le personnage
        user_id = current_user.id
        character = {
            "name": name,
            "race": race,
            "class": character_class,
            "level": level,
            "xp": 0,
            "hp": hp,
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma,
            "invisible_until": 0,
            "last_spell_used": 0
        }
        save_character(user_id, character)
        return redirect(url_for('characters'))
    return render_template('create_character.html')

# Fonction pour sauvegarder un personnage dans la base de données
def save_character(user_id, character):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO characters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        character['name'],
        character['race'],
        character['class'],
        character['level'],
        character['xp'],
        character['hp'],
        character['strength'],
        character['dexterity'],
        character['constitution'],
        character['intelligence'],
        character['wisdom'],
        character['charisma'],
        character.get('invisible_until', 0),
        character.get('last_spell_used', 0)
    ))
    conn.commit()
    conn.close()

# Démarrer l'application Flask
if __name__ == '__main__':
    app.run(debug=True, port=5000)