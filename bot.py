import discord
from discord import app_commands
import aiohttp
import asyncio
import os
from flask import Flask
import threading
import datetime

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

@app.route('/ping')
def ping():
    return "pong"

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# Discord Bot Setup
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Free Fire Regions
REGIONS = ["IND", "BD", "PK", "BR", "NA", "EU", "ME", "TR", "ID", "SG", "MY", "TH", "VN", "PH"]

# Rank mapping based on rank number
RANK_NAMES = {
    220: "Heroic", 219: "Grandmaster", 218: "Master", 
    217: "Diamond", 216: "Platinum", 215: "Gold",
    214: "Silver", 213: "Bronze"
}

class FreeFireAPI:
    def __init__(self):
        self.base_url = "https://free-ff-api-src-5plp.onrender.com/api/v1"
    
    async def get_player_stats(self, uid: str, region: str) -> dict:
        """Fetch player statistics from Free Fire API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                # Exact endpoint you provided
                url = f"https://free-ff-api-src-5plp.onrender.com/api/v1/account?region={region}&uid={uid}"
                print(f"🌐 Fetching: {url}")
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ API Response received")
                        return self.parse_player_data(data, uid, region)
                    else:
                        return {"error": f"API returned status {response.status}"}
                        
        except aiohttp.ClientError as e:
            return {"error": f"Network error: {str(e)}"}
        except asyncio.TimeoutError:
            return {"error": "API request timed out"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def parse_player_data(self, data: dict, uid: str, region: str) -> dict:
        """Parse the actual API response structure"""
        try:
            # Check if we have basicInfo (main data container)
            if 'basicInfo' not in data:
                return {"error": "No player data found in response"}
            
            basic_info = data['basicInfo']
            clan_info = data.get('clanBasicInfo', {})
            social_info = data.get('socialInfo', {})
            
            # Extract player information from the actual API structure
            result = {
                "uid": uid,
                "region": region,
                "name": basic_info.get('nickname', 'Unknown'),
                "level": basic_info.get('level', 0),
                "exp": basic_info.get('exp', 0),
                "rank_number": basic_info.get('rank', 0),
                "rank_name": RANK_NAMES.get(basic_info.get('rank', 0), "Unranked"),
                "rank_points": basic_info.get('rankingPoints', 0),
                "max_rank": RANK_NAMES.get(basic_info.get('maxRank', 0), "Unknown"),
                "clan_name": clan_info.get('clanName', 'No Clan'),
                "clan_level": clan_info.get('clanLevel', 0),
                "clan_members": f"{clan_info.get('memberNum', 0)}/{clan_info.get('capacity', 0)}",
                "likes": basic_info.get('liked', 0),
                "badges": basic_info.get('badgeCnt', 0),
                "last_login": basic_info.get('lastLoginAt', 'Unknown'),
                "status": social_info.get('signature', 'No status'),
                "season_id": basic_info.get('seasonId', 0)
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Data parsing error: {str(e)}"}

# Initialize API
ff_api = FreeFireAPI()

# SINGLE COMMAND - UID Lookup
@tree.command(name="uid", description="Get Free Fire player statistics by UID")
@app_commands.describe(uid="Player UID", region="Server region (IND, BD, PK, etc.)")
async def uid_lookup(interaction: discord.Interaction, uid: str, region: str = "IND"):
    """Get Free Fire player statistics using UID and Region"""
    await interaction.response.defer()
    
    # Validate region
    region_upper = region.upper()
    if region_upper not in REGIONS:
        valid_regions = ", ".join(REGIONS)
        await interaction.followup.send(f"❌ Invalid region! Valid: {valid_regions}")
        return
    
    # Validate UID
    if not uid.isdigit() or len(uid) < 6:
        await interaction.followup.send("❌ Invalid UID! Must be numeric and at least 6 digits.")
        return
    
    # Fetch player data
    player_data = await ff_api.get_player_stats(uid, region_upper)
    
    if "error" in player_data:
        embed = discord.Embed(
            title="❌ Player Not Found",
            description=player_data["error"],
            color=discord.Color.red()
        )
        embed.add_field(
            name="💡 Check", 
            value="• UID is correct\n• Region is correct\n• Player might be private",
            inline=False
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Create player info embed
    embed = discord.Embed(
        title=f"🎯 {player_data['name']}",
        description=f"**UID:** `{player_data['uid']}` • **Region:** {player_data['region']}",
        color=discord.Color.gold()
    )
    
    # Player Basic Info
    embed.add_field(
        name="👤 Player Info",
        value=f"**Name:** {player_data['name']}\n"
              f"**Level:** {player_data['level']}\n"
              f"**EXP:** {player_data['exp']:,}\n"
              f"**Status:** {player_data['status']}",
        inline=True
    )
    
    # Rank Info with proper rank names
    rank_emojis = {
        "Heroic": "👑", "Grandmaster": "🔥", "Master": "⚡", 
        "Diamond": "💎", "Platinum": "💠", "Gold": "🥇",
        "Silver": "🥈", "Bronze": "🥉"
    }
    
    current_rank_emoji = rank_emojis.get(player_data['rank_name'], "🎯")
    
    embed.add_field(
        name=f"{current_rank_emoji} Rank Info",
        value=f"**Rank:** {player_data['rank_name']} ({player_data['rank_number']})\n"
              f"**Points:** {player_data['rank_points']:,}\n"
              f"**Best Rank:** {player_data['max_rank']}",
        inline=True
    )
    
    # Clan Info
    embed.add_field(
        name="🏠 Clan",
        value=f"**Name:** {player_data['clan_name']}\n"
              f"**Level:** {player_data['clan_level']}\n"
              f"**Members:** {player_data['clan_members']}",
        inline=True
    )
    
    # Social Stats
    embed.add_field(
        name="📊 Social Stats",
        value=f"**Likes:** {player_data['likes']:,}\n"
              f"**Badges:** {player_data['badges']}\n"
              f"**Season:** {player_data['season_id']}",
        inline=True
    )
    
    # Additional Info
    if player_data['last_login'] != 'Unknown':
        try:
            last_login_dt = datetime.datetime.fromtimestamp(int(player_data['last_login']))
            last_login_str = last_login_dt.strftime("%Y-%m-%d %H:%M")
            embed.add_field(
                name="🕒 Last Login",
                value=last_login_str,
                inline=True
            )
        except:
            pass
    
    embed.set_footer(text="Free Fire Player Stats • Real-time Data")
    
    await interaction.followup.send(embed=embed)

@tree.command(name="servers", description="Show available Free Fire regions")
async def servers_list(interaction: discord.Interaction):
    """Show available Free Fire regions"""
    embed = discord.Embed(
        title="🌍 Free Fire Regions",
        description="Available regions for player lookup:",
        color=discord.Color.blue()
    )
    
    servers_text = ""
    for code in REGIONS:
        servers_text += f"**{code}**\n"
    
    embed.add_field(name="Region Codes", value=servers_text, inline=False)
    embed.add_field(
        name="Usage Example", 
        value="```/uid uid:1633864660 region:IND```",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Bot Events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🌐 Flask server running on port 8080')
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

# Startup
if __name__ == "__main__":
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started on port 8080")
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ ERROR: Set DISCORD_BOT_TOKEN environment variable!")
        exit(1)
    
    print("✅ Starting Free Fire UID Bot...")
    bot.run(token)