import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sqlite3
import random

# Charger les variables d'environnement
load_dotenv()

# Vérifier que le token est bien chargé
token = os.getenv('DISCORD_TOKEN')
if token is None:
    raise ValueError("Le token Discord n'a pas été trouvé dans le fichier .env")

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True  # Pour accéder au contenu des messages

# Configuration du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Désactiver la commande help par défaut
bot.remove_command('help')

# Connexion à la base de données SQLite
conn = sqlite3.connect('rpg_bot.db')
cursor = conn.cursor()

# Créer les tables si elles n'existent pas
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
        charisma INTEGER
    )
''')
conn.commit()

# Fonction pour sauvegarder un personnage
def save_character(user_id, character):
    cursor.execute('''
        INSERT OR REPLACE INTO characters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        character['charisma']
    ))
    conn.commit()

# Fonction pour charger un personnage
def load_character(user_id):
    cursor.execute('SELECT * FROM characters WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

# Dictionnaires pour gérer les quêtes, l'inventaire et les compétences
quests = {}
inventory = {}
skills = {}

# Dictionnaire pour gérer les combats en cours
combat = {}

# Événement : Quand le bot est prêt
@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user}')

# Commande : !ping
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

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
    except Exception as e:
        await ctx.send("Format invalide. Utilisez !roll NdM (ex: !roll 1d20).")

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
        "charisma": 10
    }
    save_character(user_id, character)
    await ctx.send(f"Personnage {name} créé !")

# Commande : !sheet
@bot.command()
async def sheet(ctx):
    """Affiche la fiche d'un personnage (ex: !sheet)."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        await ctx.send(f"Fiche de {character[1]}:\n{character}")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

# Commande : !spell
@bot.command()
async def spell(ctx, spell_name: str):
    """Affiche les détails d'un sort (ex: !spell Boule de Feu)."""
    spells = {
        "boule de feu": "Inflige 8d6 dégâts de feu dans une zone.",
        "soin": "Restaure 2d8 points de vie."
    }
    spell_name_lower = spell_name.lower()
    if spell_name_lower in spells:
        await ctx.send(f"{spell_name} : {spells[spell_name_lower]}")
    else:
        await ctx.send(f"Sort {spell_name} introuvable.")

# Commande : !item
@bot.command()
async def item(ctx, item_name: str):
    """Affiche les détails d'un objet (ex: !item Épée)."""
    items = {
        "épée": "Une épée tranchante pour combattre les ennemis.",
        "bouclier": "Un bouclier solide pour se protéger."
    }
    item_name_lower = item_name.lower()
    if item_name_lower in items:
        await ctx.send(f"{item_name} : {items[item_name_lower]}")
    else:
        await ctx.send(f"Objet {item_name} introuvable.")

# Commande : !start_combat
@bot.command()
async def start_combat(ctx):
    """Démarre un combat."""
    combat[ctx.guild.id] = {'participants': [], 'turn': 0}
    await ctx.send("Combat démarré ! Utilisez !join pour rejoindre.")

# Commande : !join
@bot.command()
async def join(ctx, name: str):
    """Rejoint un combat avec un personnage (ex: !join Nom)."""
    user_id = str(ctx.author.id)
    character = load_character(user_id)
    if character:
        initiative = random.randint(1, 20) + character[8]  # Dexterity est à l'index 8
        combat[ctx.guild.id]['participants'].append({'name': name, 'initiative': initiative})
        await ctx.send(f"{name} a rejoint le combat avec une initiative de {initiative}.")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

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
        else:
            await ctx.send("Aucun participant dans le combat.")
    else:
        await ctx.send("Aucun combat en cours.")

# Commande : !create_quest
@bot.command()
async def create_quest(ctx, name: str, description: str):
    """Crée une quête."""
    quests[name] = {"description": description, "completed": False}
    await ctx.send(f"Quête '{name}' créée !")

# Commande : !start_quest
@bot.command()
async def start_quest(ctx, name: str):
    """Démarre une quête."""
    if name in quests:
        quests[name]["started"] = True
        await ctx.send(f"Quête '{name}' démarrée !")
    else:
        await ctx.send(f"Quête '{name}' introuvable.")

# Commande : !complete_quest
@bot.command()
async def complete_quest(ctx, name: str):
    """Termine une quête."""
    if name in quests:
        quests[name]["completed"] = True
        await ctx.send(f"Quête '{name}' terminée !")
    else:
        await ctx.send(f"Quête '{name}' introuvable.")

# Commande : !add_item
@bot.command()
async def add_item(ctx, item: str):
    """Ajoute un objet à l'inventaire."""
    user_id = str(ctx.author.id)
    if user_id not in inventory:
        inventory[user_id] = []
    inventory[user_id].append(item)
    await ctx.send(f"{item} ajouté à ton inventaire !")

# Commande : !remove_item
@bot.command()
async def remove_item(ctx, item: str):
    """Retire un objet de l'inventaire."""
    user_id = str(ctx.author.id)
    if user_id in inventory and item in inventory[user_id]:
        inventory[user_id].remove(item)
        await ctx.send(f"{item} retiré de ton inventaire !")
    else:
        await ctx.send(f"{item} introuvable dans ton inventaire.")

# Commande : !show_inventory
@bot.command()
async def show_inventory(ctx):
    """Affiche l'inventaire du joueur."""
    user_id = str(ctx.author.id)
    if user_id in inventory and inventory[user_id]:
        await ctx.send(f"Inventaire : {', '.join(inventory[user_id])}")
    else:
        await ctx.send("Ton inventaire est vide.")

# Commande : !add_skill
@bot.command()
async def add_skill(ctx, skill: str):
    """Ajoute une compétence au personnage."""
    user_id = str(ctx.author.id)
    if user_id not in skills:
        skills[user_id] = []
    skills[user_id].append(skill)
    await ctx.send(f"Compétence '{skill}' ajoutée !")

# Commande : !use_skill
@bot.command()
async def use_skill(ctx, skill: str):
    """Utilise une compétence."""
    user_id = str(ctx.author.id)
    if user_id in skills and skill in skills[user_id]:
        await ctx.send(f"Tu utilises la compétence '{skill}' !")
    else:
        await ctx.send(f"Compétence '{skill}' introuvable.")

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
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

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
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

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
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

# Commande : !help
@bot.command()
async def help(ctx):
    """Affiche les commandes disponibles."""
    help_message = """
    **Commandes disponibles :**
    - `!ping` : Vérifie que le bot fonctionne.
    - `!roll <dice>` : Lance des dés (ex: `!roll 1d20`).
    - `!create <name>` : Crée une fiche de personnage.
    - `!sheet` : Affiche la fiche de ton personnage.
    - `!spell <name>` : Affiche les détails d'un sort.
    - `!item <name>` : Affiche les détails d'un objet.
    - `!start_combat` : Démarre un combat.
    - `!join <name>` : Rejoint un combat.
    - `!next_turn` : Passe au tour suivant.
    - `!create_quest <name> <description>` : Crée une quête.
    - `!start_quest <name>` : Démarre une quête.
    - `!complete_quest <name>` : Termine une quête.
    - `!add_item <item>` : Ajoute un objet à l'inventaire.
    - `!remove_item <item>` : Retire un objet de l'inventaire.
    - `!show_inventory` : Affiche l'inventaire.
    - `!add_skill <skill>` : Ajoute une compétence.
    - `!use_skill <skill>` : Utilise une compétence.
    - `!take_damage <amount>` : Inflige des dégâts au personnage.
    - `!heal <amount>` : Soigne le personnage.
    - `!gain_xp <amount>` : Ajoute de l'expérience au personnage.
    """
    await ctx.send(help_message)

# Lancer le bot
bot.run(token)