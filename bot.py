import discord
from discord import app_commands
import aiohttp
import asyncio
import os
from flask import Flask
import threading
import datetime
from typing import Literal

# Flask app for uptime monitoring
app = Flask(__name__)

@app.route('/')
def home():
    return "🎯 Free Fire UID Bot is running!"

@app.route('/health')
def health_check():
    return {
        "status": "healthy", 
        "service": "Free Fire UID Bot",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# Discord Bot Setup
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Free Fire Servers (lowercase as shown in example)
SERVERS = ["ind", "bd", "pk", "br", "na", "eu", "me", "tr", "id", "sg", "my", "th", "vn", "ph"]

# Game Modes and Match Modes (exact from example)
GAME_MODES = ["br", "cs"]
MATCH_MODES = ["CAREER", "NORMAL", "RANKED"]

class FreeFireAPI:
    def __init__(self):
        self.base_url = "https://freefire-api-skxvercel.app"
    
    async def get_player_stats(self, uid: str, server: str, gamemode: str = "br", matchmode: str = "CAREER") -> dict:
        """Fetch player statistics using EXACT URL from your example"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                # ✅ EXACT URL STRUCTURE FROM YOUR EXAMPLE
                url = f"https://freefire-api-skxvercel.app/get_player_stats?server={server}&uid={uid}&matchmode={matchmode}&gamemode={gamemode}"
                print(f"🌐 Fetching: {url}")
                
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ API Response received")
                        return self.parse_player_data(data, uid, server, gamemode, matchmode)
                    else:
                        return {"error": f"API returned status {response.status}"}
                        
        except aiohttp.ClientError as e:
            return {"error": f"Network error: {str(e)}"}
        except asyncio.TimeoutError:
            return {"error": "API request timed out"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def parse_player_data(self, data: dict, uid: str, server: str, gamemode: str, matchmode: str) -> dict:
        """Parse API response into structured data"""
        try:
            # Check if data is valid
            if not data or isinstance(data, dict) and data.get('status') == 'error':
                return {"error": "No player data found or invalid UID"}
            
            # The API might return data directly or nested
            player_data = data.get('data', data)  # Try 'data' key first, else use root
            
            # Extract basic info
            basic_info = player_data.get('basicInfo', {})
            clan_info = player_data.get('clanBasicInfo', {})
            stats = player_data.get('stats', {})
            
            result = {
                "uid": uid,
                "server": server.upper(),
                "gamemode": gamemode.upper(),
                "matchmode": matchmode,
                "name": basic_info.get('nickname', 'Unknown'),
                "level": basic_info.get('level', 0),
                "exp": basic_info.get('exp', 0),
                "rank_points": basic_info.get('rankingPoints', 0),
                "clan_name": clan_info.get('clanName', 'No Clan'),
                "clan_level": clan_info.get('clanLevel', 0),
                "likes": basic_info.get('liked', 0),
                
                # Game stats
                "matches_played": stats.get('matchesPlayed', 0),
                "kills": stats.get('kills', 0),
                "headshots": stats.get('headshots', 0),
                "damage": stats.get('damage', 0),
                "wins": stats.get('wins', 0),
                "top_3": stats.get('top3', 0),
                "top_6": stats.get('top6', 0),
                "survival_time": stats.get('survivalTime', 0),
            }
            
            # Calculate ratios
            if result['matches_played'] > 0:
                result['win_rate'] = round((result['wins'] / result['matches_played']) * 100, 2)
                deaths = result['matches_played'] - result['wins']
                result['kd_ratio'] = round(result['kills'] / max(deaths, 1), 2)
            else:
                result['win_rate'] = 0
                result['kd_ratio'] = 0
            
            return result
            
        except Exception as e:
            return {"error": f"Data parsing error: {str(e)}"}

# Initialize API
ff_api = FreeFireAPI()

# SLASH COMMANDS

@tree.command(name="stats", description="Get Free Fire player statistics")
@app_commands.describe(
    uid="Player UID",
    server="Server region (ind, bd, pk, etc.)",
    gamemode="Game mode (br, cs)",
    matchmode="Match mode"
)
async def player_stats(
    interaction: discord.Interaction, 
    uid: str,
    server: str = "ind",
    gamemode: Literal["br", "cs"] = "br",
    matchmode: Literal["CAREER", "NORMAL", "RANKED"] = "CAREER"
):
    """Get Free Fire player stats using the exact API from your example"""
    await interaction.response.defer()
    
    # Validate UID
    if not uid.isdigit() or len(uid) < 6:
        await interaction.followup.send("❌ Invalid UID! Must be numeric and at least 6 digits.")
        return
    
    # Fetch player data using EXACT URL format from your example
    player_data = await ff_api.get_player_stats(uid, server, gamemode, matchmode)
    
    if "error" in player_data:
        embed = discord.Embed(
            title="❌ Player Not Found",
            description=player_data["error"],
            color=discord.Color.red()
        )
        embed.add_field(
            name="💡 Try This Example",
            value="`/stats uid:11959685790 server:ind matchmode:RANKED gamemode:br`",
            inline=False
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Create stats embed
    embed = discord.Embed(
        title=f"🎯 {player_data['name']}",
        description=f"**UID:** `{player_data['uid']}` • **Server:** {player_data['server']}",
        color=discord.Color.gold()
    )
    
    # Basic Info
    embed.add_field(
        name="👤 Player Info",
        value=f"**Name:** {player_data['name']}\n**Level:** {player_data['level']}\n**Clan:** {player_data['clan_name']}",
        inline=True
    )
    
    # Game Mode Info
    embed.add_field(
        name="🎮 Mode",
        value=f"**Type:** {player_data['gamemode'].upper()}\n**Match:** {player_data['matchmode']}\n**Likes:** {player_data['likes']:,}",
        inline=True
    )
    
    # Match Stats
    embed.add_field(
        name="📊 Matches",
        value=f"**Played:** {player_data['matches_played']:,}\n**Wins:** {player_data['wins']:,}\n**WR:** {player_data['win_rate']}%",
        inline=True
    )
    
    # Combat Stats
    embed.add_field(
        name="⚔️ Combat",
        value=f"**Kills:** {player_data['kills']:,}\n**KD:** {player_data['kd_ratio']}\n**HS:** {player_data['headshots']:,}",
        inline=True
    )
    
    # Performance
    embed.add_field(
        name="📈 Performance",
        value=f"**Damage:** {player_data['damage']:,}\n**Top 3:** {player_data['top_3']:,}\n**Survival:** {player_data['survival_time']}s",
        inline=True
    )
    
    embed.set_footer(text=f"Free Fire Stats • {player_data['gamemode'].upper()} • {player_data['matchmode']}")
    
    await interaction.followup.send(embed=embed)

@tree.command(name="example", description="Show usage example")
async def example_command(interaction: discord.Interaction):
    """Show example usage"""
    embed = discord.Embed(
        title="📋 Usage Examples",
        color=discord.Color.blue()
    )
    
    examples = """
    **Basic Usage:**
    `/stats uid:11959685790 server:ind`
    
    **Ranked Battle Royale:**
    `/stats uid:11959685790 server:ind matchmode:RANKED gamemode:br`
    
    **Clash Squad:**
    `/stats uid:11959685790 server:pk gamemode:cs`
    
    **Different Server:**
    `/stats uid:11959685790 server:bd matchmode:NORMAL`
    """
    
    embed.add_field(name="Commands", value=examples, inline=False)
    embed.add_field(
        name="Available Servers", 
        value=", ".join([f"`{s}`" for s in SERVERS]),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Bot Events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🌐 Flask server running on port 8080')
    
    # Instant command sync
    YOUR_GUILD_ID = 1425015639126442005  # Replace with your server ID
    
    try:
        guild = discord.Object(id=YOUR_GUILD_ID)
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
        print(f"✅ Instantly synced {len(synced)} commands to your server")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

# Startup
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started on port 8080")
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ ERROR: Set DISCORD_BOT_TOKEN environment variable!")
        exit(1)
    
    print("✅ Starting Free Fire Stats Bot...")
    bot.run(token)
