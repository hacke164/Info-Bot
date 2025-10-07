import discord
from discord import app_commands
import aiohttp
import asyncio
import os
from flask import Flask, jsonify
import threading
import datetime
from typing import Literal

# Flask app for uptime monitoring
app = Flask(__name__)

@app.route('/')
def home():
    return "🎯 Free Fire Like Bot is running!"

@app.route('/health')
def health_check():
    return {
        "status": "healthy", 
        "service": "Free Fire Like Bot",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# Discord Bot Setup
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Free Fire Servers
SERVERS = ["ind", "bd", "pk", "br", "na", "eu", "me", "tr", "id", "sg", "my", "th", "vn", "ph"]

class FreeFireLikeAPI:
    def __init__(self):
        self.base_url = "https://like-api-nine.vercel.app/like"
        self.api_key = "lumina"  # From your API documentation
    
    async def send_like(self, uid: str, server_name: str) -> dict:
        """Send like to Free Fire player using the exact API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                # ✅ EXACT URL STRUCTURE from your example
                url = f"{self.base_url}?uid={uid}&server_name={server_name}&key={self.api_key}"
                print(f"🌐 Sending like: {url}")
                
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Like API Response: {data}")
                        return self.parse_like_response(data, uid, server_name)
                    else:
                        return {"error": f"API returned status {response.status}"}
                        
        except aiohttp.ClientError as e:
            return {"error": f"Network error: {str(e)}"}
        except asyncio.TimeoutError:
            return {"error": "API request timed out"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def parse_like_response(self, data: dict, uid: str, server_name: str) -> dict:
        """Parse the like API response"""
        try:
            # Check if data is valid
            if not data:
                return {"error": "No response from API"}
            
            # Map API response to our structure
            result = {
                "uid": uid,
                "server": server_name.upper(),
                "likes_given_by_api": data.get("LikesGivenByAPI", 0),
                "likes_after_command": data.get("LikesafterCommand", 0),
                "likes_before_command": data.get("LikesbeforeCommand", 0),
                "player_nickname": data.get("PlayerNickname", "Unknown"),
                "remains": data.get("remains", "Unknown"),
                "status": data.get("status", -1),
                "raw_response": data
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Data parsing error: {str(e)}"}

# Initialize API
ff_like_api = FreeFireLikeAPI()

# SLASH COMMANDS

@tree.command(name="like", description="Send like to Free Fire player")
@app_commands.describe(
    uid="Player UID",
    server="Server region (ind, bd, pk, etc.)"
)
async def send_like_command(
    interaction: discord.Interaction, 
    uid: str,
    server: str = "ind"
):
    """Send like to Free Fire player using the exact API"""
    await interaction.response.defer()
    
    # Validate UID
    if not uid.isdigit() or len(uid) < 6:
        await interaction.followup.send("❌ Invalid UID! Must be numeric and at least 6 digits.")
        return
    
    # Validate server
    if server.lower() not in SERVERS:
        await interaction.followup.send(f"❌ Invalid server! Available: {', '.join(SERVERS)}")
        return
    
    # Send like via API
    like_result = await ff_like_api.send_like(uid, server.lower())
    
    if "error" in like_result:
        embed = discord.Embed(
            title="❌ Like Failed",
            description=like_result["error"],
            color=discord.Color.red()
        )
        embed.add_field(
            name="💡 Try This Example",
            value="`/like uid:12662268769 server:ind`",
            inline=False
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Create success embed based on status code
    status = like_result["status"]
    
    if status == 2:  # Success status from your API example
        embed = discord.Embed(
            title="✅ Like Sent Successfully!",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="⚠️ Like Action Completed",
            color=discord.Color.orange()
        )
    
    # Player Info
    embed.add_field(
        name="👤 Player Info",
        value=f"**Name:** {like_result['player_nickname']}\n**UID:** `{like_result['uid']}`\n**Server:** {like_result['server']}",
        inline=True
    )
    
    # Like Statistics
    embed.add_field(
        name="❤️ Like Stats",
        value=f"**Before:** {like_result['likes_before_command']}\n**After:** {like_result['likes_after_command']}\n**Given:** {like_result['likes_given_by_api']}",
        inline=True
    )
    
    # Additional Info
    embed.add_field(
        name="📊 Status",
        value=f"**Code:** {like_result['status']}\n**Remains:** {like_result['remains']}",
        inline=True
    )
    
    embed.set_footer(text="Free Fire Like Bot • Powered by Like API")
    
    await interaction.followup.send(embed=embed)

@tree.command(name="servers", description="Show available Free Fire servers")
async def servers_command(interaction: discord.Interaction):
    """Show available servers"""
    embed = discord.Embed(
        title="🌍 Available Free Fire Servers",
        color=discord.Color.blue()
    )
    
    servers_list = "\n".join([f"• **{server.upper()}**" for server in SERVERS])
    embed.add_field(name="Servers", value=servers_list, inline=False)
    
    embed.add_field(
        name="📋 Usage Example",
        value="`/like uid:12662268769 server:ind`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="example", description="Show usage example")
async def example_command(interaction: discord.Interaction):
    """Show example usage"""
    embed = discord.Embed(
        title="📋 Usage Examples",
        color=discord.Color.gold()
    )
    
    examples = """
    **Basic Usage:**
    `/like uid:12662268769 server:ind`
    
    **Different Server:**
    `/like uid:12662268769 server:bd`
    
    **Pakistan Server:**
    `/like uid:12662268769 server:pk`
    
    **Brazil Server:**
    `/like uid:12662268769 server:br`
    """
    
    embed.add_field(name="Commands", value=examples, inline=False)
    
    embed.add_field(
        name="🎯 Example from API",
        value="UID: `12662268769`\nServer: `ind`\nPlayer: `PANEL_P0WER?`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Bot Events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🌐 Flask server running on port 8080')
    
    # Instant command sync
    YOUR_GUILD_ID = 1423949867406852160  # Replace with your server ID
    
    try:
        guild = discord.Object(id=YOUR_GUILD_ID)
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
        print(f"✅ Instantly synced {len(synced)} commands to your server")
        
        # Also sync globally
        global_synced = await tree.sync()
        print(f"✅ Synced {len(global_synced)} commands globally")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

# Startup
if __name__ == "__main__":
    # Start Flask server in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started on port 8080")
    
    # Get bot token from environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ ERROR: Set DISCORD_BOT_TOKEN environment variable!")
        exit(1)
    
    print("✅ Starting Free Fire Like Bot...")
    bot.run(token)
