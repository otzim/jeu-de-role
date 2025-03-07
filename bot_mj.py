import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import random
import sqlite3

# Charger les variables d'environnement
load_dotenv()

# Vérifier que le token est bien chargé
token = os.getenv('DISCORD_TOKEN')
if token is None:
    raise ValueError("Le token Discord n'a pas été trouvé dans le fichier .env")

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True  # Pour accéder au contenu des messages
intents.members = True  # Pour accéder aux membres du serveur (optionnel)

# Configuration du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Connexion à la base de données SQLite
conn = sqlite3.connect('rpg.db')
cursor = conn.cursor()

# Créer les tables si elles n'existent pas
cursor.execute('''
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    race TEXT,
    class TEXT,
    level INTEGER,
    hp INTEGER,
    strength INTEGER,
    dexterity INTEGER,
    constitution INTEGER,
    intelligence INTEGER,
    wisdom INTEGER,
    charisma INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS spells (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
)
''')
conn.commit()

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
    cursor.execute('INSERT INTO characters (name) VALUES (?)', (name,))
    conn.commit()
    await ctx.send(f"Personnage {name} créé !")

# Commande : !sheet
@bot.command()
async def sheet(ctx, name: str):
    """Affiche la fiche d'un personnage (ex: !sheet Nom)."""
    cursor.execute('SELECT * FROM characters WHERE name = ?', (name,))
    character = cursor.fetchone()
    if character is None:
        await ctx.send(f"Personnage {name} introuvable.")
        return
    await ctx.send(f"Fiche de {name}:\n{character}")

# Commande : !spell
@bot.command()
async def spell(ctx, spell_name: str):
    """Affiche les détails d'un sort (ex: !spell Boule de Feu)."""
    cursor.execute('SELECT description FROM spells WHERE name = ?', (spell_name,))
    spell = cursor.fetchone()
    if spell is None:
        await ctx.send(f"Sort {spell_name} introuvable.")
        return
    await ctx.send(f"{spell_name} : {spell[0]}")

# Commande : !item
@bot.command()
async def item(ctx, item_name: str):
    """Affiche les détails d'un objet (ex: !item Épée)."""
    cursor.execute('SELECT description FROM items WHERE name = ?', (item_name,))
    item = cursor.fetchone()
    if item is None:
        await ctx.send(f"Objet {item_name} introuvable.")
        return
    await ctx.send(f"{item_name} : {item[0]}")

# Gestion des combats
combat = {}  # Stocke les combats en cours

@bot.command()
async def start_combat(ctx):
    """Démarre un combat."""
    combat[ctx.guild.id] = {'participants': [], 'turn': 0}
    await ctx.send("Combat démarré ! Utilisez !join pour rejoindre.")

@bot.command()
async def join(ctx, name: str):
    """Rejoint le combat avec un personnage (ex: !join Nom)."""
    if name not in [character[1] for character in cursor.execute('SELECT name FROM characters').fetchall()]:
        await ctx.send(f"Personnage {name} introuvable.")
        return
    if ctx.guild.id not in combat:
        await ctx.send("Aucun combat en cours.")
        return
    initiative = random.randint(1, 20) + cursor.execute('SELECT dexterity FROM characters WHERE name = ?', (name,)).fetchone()[0]
    combat[ctx.guild.id]['participants'].append({'name': name, 'initiative': initiative})
    await ctx.send(f"{name} a rejoint le combat avec une initiative de {initiative}.")

@bot.command()
async def next_turn(ctx):
    """Passe au tour suivant."""
    if ctx.guild.id not in combat:
        await ctx.send("Aucun combat en cours.")
        return
    participants = combat[ctx.guild.id]['participants']
    if not participants:
        await ctx.send("Aucun participant dans le combat.")
        return
    participants.sort(key=lambda x: x['initiative'], reverse=True)
    current_turn = combat[ctx.guild.id]['turn'] % len(participants)
    current_player = participants[current_turn]
    combat[ctx.guild.id]['turn'] += 1
    await ctx.send(f"C'est au tour de {current_player['name']} !")

# Lancer le bot
bot.run(token)