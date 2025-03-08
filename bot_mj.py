import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import json
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

# Charger les données
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

# Fichiers de données
characters_file = "data/characters.json"
quests_file = "data/quests.json"
inventory_file = "data/inventory.json"
skills_file = "data/skills.json"

characters = load_data(characters_file)
quests = load_data(quests_file)
inventory = load_data(inventory_file)
skills = load_data(skills_file)

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
    characters[user_id] = {
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
    save_data(characters_file, characters)
    await ctx.send(f"Personnage {name} créé !")

# Commande : !sheet
@bot.command()
async def sheet(ctx):
    """Affiche la fiche d'un personnage (ex: !sheet)."""
    user_id = str(ctx.author.id)
    if user_id in characters:
        await ctx.send(f"Fiche de {characters[user_id]['name']}:\n{json.dumps(characters[user_id], indent=2)}")
    else:
        await ctx.send("Tu n'as pas encore de personnage. Utilise `!create` pour en créer un.")

# Commande : !spell
@bot.command()
async def spell(ctx, spell_name: str):
    """Affiche les détails d'un sort (ex: !spell Boule de Feu)."""
    spells = {
        "Boule de Feu": "Inflige 8d6 dégâts de feu dans une zone.",
        "Soin": "Restaure 2d8 points de vie."
    }
    if spell_name in spells:
        await ctx.send(f"{spell_name} : {spells[spell_name]}")
    else:
        await ctx.send(f"Sort {spell_name} introuvable.")

# Commande : !item
@bot.command()
async def item(ctx, item_name: str):
    """Affiche les détails d'un objet (ex: !item Épée)."""
    items = {
        "Épée": "Une épée tranchante pour combattre les ennemis.",
        "Bouclier": "Un bouclier solide pour se protéger."
    }
    if item_name in items:
        await ctx.send(f"{item_name} : {items[item_name]}")
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
    if user_id in characters:
        initiative = random.randint(1, 20) + characters[user_id]['dexterity']
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
    """
    await ctx.send(help_message)

# Lancer le bot
bot.run(token)