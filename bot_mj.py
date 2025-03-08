import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sqlite3
import random
import logging
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from threading import Thread
from functools import wraps

# Charger les variables d'environnement
load_dotenv()

# Configuration des logs
logging.basicConfig(
    filename='rpg_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("Démarrage du bot RPG")

# Vérifier que le token est bien chargé
token = os.getenv('DISCORD_TOKEN')
if token is None:
    logging.error("Le token Discord n'a pas été trouvé dans le fichier .env")
    raise ValueError("Le token Discord n'a pas été trouvé dans le fichier .env")

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True  # Pour accéder au contenu des messages

# Configuration du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Désactiver la commande help par défaut
bot.remove_command('help')

# Connexion à la base de données SQLite
conn = sqlite3.connect('rpg_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Supprimer la table si elle existe
cursor.execute('DROP TABLE IF EXISTS characters')

# Recréer la table avec la bonne structure
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

# Valider les changements
conn.commit()

print("La table 'characters' a été mise à jour avec succès.")

# Fonction pour sauvegarder un personnage
def save_character(user_id, character):
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
    logging.info(f"Personnage {character['name']} sauvegardé pour l'utilisateur {user_id}")

# Fonction pour charger un personnage
def load_character(user_id):
    cursor.execute('SELECT * FROM characters WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "user_id": row[0],
            "name": row[1],
            "race": row[2],
            "class": row[3],
            "level": row[4],
            "xp": row[5],
            "hp": row[6],
            "strength": row[7],
            "dexterity": row[8],
            "constitution": row[9],
            "intelligence": row[10],
            "wisdom": row[11],
            "charisma": row[12],
            "invisible_until": row[13],
            "last_spell_used": row[14]
        }
    return None

# Dictionnaires pour gérer les quêtes, l'inventaire et les compétences
quests = {}
inventory = {}
skills = {}

# Dictionnaire pour gérer les combats en cours
combat = {}

# Événement : Quand le bot est prêt
@bot.event
async def on_ready():
    logging.info(f'Bot connecté en tant que {bot.user}')
    print(f'Bot connecté en tant que {bot.user}')

# Commande : !ping
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')
    logging.info(f"Commande !ping utilisée par {ctx.author}")

# Commande : !roll
@bot.command()
async def roll(ctx, dice: str):
    """Lance des dés (ex: !roll 1d20)."""
    try:
        num_dice, dice_type = map(int, dice.split('d'))
        if num_dice < 1 or dice_type < 2:
            await ctx.send("Format invalide. Utilisez !roll NdM (ex: !roll 1d20).")
            return
        rolls = [random.randint(1, dice_type) for _ in range(num_dice)]
        total = sum(rolls)
        await ctx.send(f'Résultat : {rolls} (Total: {total})')
        logging.info(f"Commande !roll utilisée par {ctx.author} : {dice} -> {rolls} (Total: {total})")
    except Exception as e:
        await ctx.send("Format invalide. Utilisez !roll NdM (ex: !roll 1d20).")
        logging.error(f"Erreur avec la commande !roll : {e}")

# Commande : !create
@bot.command()
async def create(ctx, name: str):
    """Crée une fiche de personnage (ex: !create Nom)."""
    user_id = str(ctx.author.id)
    character = {
        "name": name,
        "race": "Humain",
        "class": "Guerrier",
        "level": 1,
        "xp": 0,
        "hp": 10,
        "strength": 10,
        "dexterity": 10,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
        "invisible_until": 0,
        "last_spell_used": 0
    }
    save_character(user_id, character)
    await ctx.send(f"Personnage {name} créé !")
    logging.info(f"Personnage {name} créé par {ctx.author}")

# Commande : !sheet
@bot.command()
async def sheet(ctx):
    """Affiche la fiche d'un personnage (ex: !sheet)."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        await ctx.send(f"Fiche de {character['name']}:\n{character}")
        logging.info(f"Fiche de personnage affichée pour {ctx.author}")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")
        logging.warning(f"{ctx.author} a tenté d'afficher une fiche de personnage inexistante.")

# Commande : !spell
@bot.command()
async def spell(ctx, spell_name: str):
    """Affiche les détails d'un sort (ex: !spell Boule de Feu)."""
    spells = {
        "boule de feu": "Inflige 8d6 dégâts de feu dans une zone.",
        "soin": "Restaure 2d8 points de vie.",
        "invisibilité": "Rend le personnage invisible pendant 1 minute ou jusqu'à ce qu'il attaque ou lance un sort.",
        "éclair": "Inflige 1d10 dégâts de foudre à une cible."
    }
    spell_name_lower = spell_name.lower()
    if spell_name_lower in spells:
        await ctx.send(f"{spell_name} : {spells[spell_name_lower]}")
    else:
        await ctx.send(f"Sort {spell_name} introuvable.")

# Commande : !use_soin
@bot.command()
async def use_soin(ctx):
    """Utilise le sort Soin pour restaurer des points de vie."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        current_time = int(time.time())
        if current_time - character.get('last_spell_used', 0) < 60:  # Cooldown de 60 secondes
            await ctx.send("Vous devez attendre avant de pouvoir utiliser un sort à nouveau.")
            return
        heal_amount = random.randint(2, 16)  # 2d8
        character["hp"] += heal_amount
        character["last_spell_used"] = current_time
        save_character(user_id, character)
        await ctx.send(f"{character['name']} a été soigné de {heal_amount} PV. Il a maintenant {character['hp']} PV.")
        logging.info(f"{ctx.author} a utilisé le sort Soin et a restauré {heal_amount} PV.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

# Commande : !use_invisibilite
@bot.command()
async def use_invisibilite(ctx):
    """Utilise le sort Invisibilité pour rendre le personnage invisible."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        current_time = int(time.time())
        if current_time - character.get('last_spell_used', 0) < 60:  # Cooldown de 60 secondes
            await ctx.send("Vous devez attendre avant de pouvoir utiliser un sort à nouveau.")
            return
        character["invisible_until"] = current_time + 60  # Invisible pendant 60 secondes
        character["last_spell_used"] = current_time
        save_character(user_id, character)
        await ctx.send(f"{character['name']} devient invisible pendant 1 minute ou jusqu'à ce qu'il attaque ou lance un sort.")
        logging.info(f"{ctx.author} a utilisé le sort Invisibilité.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

# Commande : !use_eclair
@bot.command()
async def use_eclair(ctx, target: discord.Member = None):
    """Utilise le sort Éclair pour infliger des dégâts à une cible."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        current_time = int(time.time())
        if current_time - character.get('last_spell_used', 0) < 60:  # Cooldown de 60 secondes
            await ctx.send("Vous devez attendre avant de pouvoir utiliser un sort à nouveau.")
            return
        if target is None:
            await ctx.send("Vous devez cibler un joueur pour utiliser ce sort.")
            return
        target_character = load_character(str(target.id))
        if target_character is None:
            await ctx.send("La cible n'a pas de personnage.")
            return
        damage = random.randint(1, 10)  # 1d10
        target_character["hp"] -= damage
        save_character(str(target.id), target_character)
        character["last_spell_used"] = current_time
        save_character(user_id, character)
        await ctx.send(f"{character['name']} lance Éclair et inflige {damage} dégâts de foudre à {target_character['name']} !")
        logging.info(f"{ctx.author} a utilisé le sort Éclair et a infligé {damage} dégâts à {target}.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

# Commande : !start_combat
@bot.command()
async def start_combat(ctx):
    """Démarre un combat."""
    combat[ctx.guild.id] = {'participants': [], 'turn': 0}
    await ctx.send("Combat démarré ! Utilisez !join pour rejoindre.")
    logging.info(f"Combat démarré par {ctx.author}.")

# Commande : !join
@bot.command()
async def join(ctx, name: str):
    """Rejoint un combat avec un personnage (ex: !join Nom)."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        initiative = random.randint(1, 20) + character["dexterity"]  # Ajouter la dextérité à l'initiative
        if ctx.guild.id not in combat:
            combat[ctx.guild.id] = {'participants': [], 'turn': 0}
        combat[ctx.guild.id]['participants'].append({'name': name, 'initiative': initiative})
        await ctx.send(f"{name} a rejoint le combat avec une initiative de {initiative}.")
        logging.info(f"{ctx.author} a rejoint le combat avec {name} (initiative: {initiative}).")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")
        logging.warning(f"{ctx.author} a tenté de rejoindre un combat sans personnage.")

# Commande : !next_turn
@bot.command()
async def next_turn(ctx):
    """Passe au tour suivant."""
    if ctx.guild.id in combat:
        participants = combat[ctx.guild.id]['participants']
        if participants:
            participants.sort(key=lambda x: x['initiative'], reverse=True)
            current_turn = combat[ctx.guild.id]['turn'] % len(participants)
            current_player = participants[current_turn]
            combat[ctx.guild.id]['turn'] += 1
            await ctx.send(f"C'est au tour de {current_player['name']} !")
            logging.info(f"Tour suivant dans le combat : {current_player['name']}.")
        else:
            await ctx.send("Aucun participant dans le combat.")
            logging.warning(f"{ctx.author} a tenté de passer au tour suivant sans participants.")
    else:
        await ctx.send("Aucun combat en cours.")
        logging.warning(f"{ctx.author} a tenté de passer au tour suivant sans combat en cours.")

# Commande : !create_quest
@bot.command()
async def create_quest(ctx, name: str, description: str):
    """Crée une quête."""
    quests[name] = {"description": description, "completed": False}
    await ctx.send(f"Quête '{name}' créée !")
    logging.info(f"Quête '{name}' créée par {ctx.author}.")

# Commande : !start_quest
@bot.command()
async def start_quest(ctx, name: str):
    """Démarre une quête."""
    if name in quests:
        quests[name]["started"] = True
        await ctx.send(f"Quête '{name}' démarrée !")
        logging.info(f"Quête '{name}' démarrée par {ctx.author}.")
    else:
        await ctx.send(f"Quête '{name}' introuvable.")
        logging.warning(f"{ctx.author} a tenté de démarrer une quête introuvable : {name}.")

# Commande : !complete_quest
@bot.command()
async def complete_quest(ctx, name: str):
    """Termine une quête."""
    if name in quests:
        quests[name]["completed"] = True
        await ctx.send(f"Quête '{name}' terminée !")
        logging.info(f"Quête '{name}' terminée par {ctx.author}.")
    else:
        await ctx.send(f"Quête '{name}' introuvable.")
        logging.warning(f"{ctx.author} a tenté de terminer une quête introuvable : {name}.")

# Commande : !add_item
@bot.command()
async def add_item(ctx, item: str):
    """Ajoute un objet à l'inventaire."""
    user_id = str(ctx.author.id)
    if user_id not in inventory:
        inventory[user_id] = []
    inventory[user_id].append(item)
    await ctx.send(f"{item} ajouté à ton inventaire !")
    logging.info(f"{ctx.author} a ajouté '{item}' à son inventaire.")

# Commande : !remove_item
@bot.command()
async def remove_item(ctx, item: str):
    """Retire un objet de l'inventaire."""
    user_id = str(ctx.author.id)
    if user_id in inventory and item in inventory[user_id]:
        inventory[user_id].remove(item)
        await ctx.send(f"{item} retiré de ton inventaire !")
        logging.info(f"{ctx.author} a retiré '{item}' de son inventaire.")
    else:
        await ctx.send(f"{item} introuvable dans ton inventaire.")
        logging.warning(f"{ctx.author} a tenté de retirer un objet introuvable : {item}.")

# Commande : !show_inventory
@bot.command()
async def show_inventory(ctx):
    """Affiche l'inventaire du joueur."""
    user_id = str(ctx.author.id)
    if user_id in inventory and inventory[user_id]:
        await ctx.send(f"Inventaire : {', '.join(inventory[user_id])}")
        logging.info(f"{ctx.author} a affiché son inventaire.")
    else:
        await ctx.send("Ton inventaire est vide.")
        logging.warning(f"{ctx.author} a tenté d'afficher un inventaire vide.")

# Commande : !add_skill
@bot.command()
async def add_skill(ctx, skill: str):
    """Ajoute une compétence au personnage."""
    user_id = str(ctx.author.id)
    if user_id not in skills:
        skills[user_id] = []
    skills[user_id].append(skill)
    await ctx.send(f"Compétence '{skill}' ajoutée !")
    logging.info(f"{ctx.author} a ajouté la compétence '{skill}'.")

# Commande : !use_skill
@bot.command()
async def use_skill(ctx, skill: str):
    """Utilise une compétence."""
    user_id = str(ctx.author.id)
    if user_id in skills and skill in skills[user_id]:
        await ctx.send(f"Tu utilises la compétence '{skill}' !")
        logging.info(f"{ctx.author} a utilisé la compétence '{skill}'.")
    else:
        await ctx.send(f"Compétence '{skill}' introuvable.")
        logging.warning(f"{ctx.author} a tenté d'utiliser une compétence introuvable : {skill}.")

# Commande : !take_damage
@bot.command()
async def take_damage(ctx, amount: int):
    """Inflige des dégâts au personnage."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        character["hp"] -= amount
        if character["hp"] <= 0:
            await ctx.send(f"{character['name']} est mort !")
        else:
            await ctx.send(f"{character['name']} a perdu {amount} PV. Il lui reste {character['hp']} PV.")
        save_character(user_id, character)
        logging.info(f"{ctx.author} a subi {amount} dégâts. PV restants : {character['hp']}.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")
        logging.warning(f"{ctx.author} a tenté de subir des dégâts sans personnage.")

# Commande : !heal
@bot.command()
async def heal(ctx, amount: int):
    """Soigne le personnage."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        character["hp"] += amount
        await ctx.send(f"{character['name']} a été soigné de {amount} PV. Il a maintenant {character['hp']} PV.")
        save_character(user_id, character)
        logging.info(f"{ctx.author} a été soigné de {amount} PV. PV restants : {character['hp']}.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")
        logging.warning(f"{ctx.author} a tenté de se soigner sans personnage.")

# Commande : !gain_xp
@bot.command()
async def gain_xp(ctx, amount: int):
    """Ajoute de l'expérience au personnage."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        character["xp"] += amount
        if character["xp"] >= 100:  # Exemple : 100 XP pour monter de niveau
            character["level"] += 1
            character["xp"] = 0
            await ctx.send(f"Félicitations ! {character['name']} est maintenant niveau {character['level']}.")
        save_character(user_id, character)
        await ctx.send(f"{amount} XP ajoutés à {character['name']}.")
        logging.info(f"{ctx.author} a gagné {amount} XP. Niveau actuel : {character['level']}.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")
        logging.warning(f"{ctx.author} a tenté de gagner de l'XP sans personnage.")

# Interface Web avec Flask
app = Flask(__name__)
auth = HTTPBasicAuth()

# Configuration de l'authentification
users = {
    "admin": os.getenv('WEB_PASSWORD', 'password')
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

@app.route('/')
@auth.login_required
def index():
    return redirect(url_for('characters'))

@app.route('/characters')
@auth.login_required
def characters():
    cursor.execute('SELECT * FROM characters')
    characters = cursor.fetchall()
    return render_template('characters.html', characters=characters)

@app.route('/quests')
@auth.login_required
def quests_page():
    return render_template('quests.html', quests=quests)

@app.route('/create_quest', methods=['POST'])
@auth.login_required
def create_quest():
    quest_name = request.form.get('name')
    quest_description = request.form.get('description')
    if quest_name and quest_description:
        quests[quest_name] = {"description": quest_description, "completed": False}
        logging.info(f"Quête '{quest_name}' créée via l'interface web.")
    return redirect(url_for('quests_page'))

# Lancer le serveur Flask dans un thread séparé
def run_flask():
    app.run(port=5000)

flask_thread = Thread(target=run_flask)
flask_thread.start()

# Lancer le bot
bot.run(token)