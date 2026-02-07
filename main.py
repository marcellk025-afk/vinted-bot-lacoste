import discord
from discord.ext import tasks
from discord.ui import Button, View
import requests
import os
import random
import asyncio
from datetime import datetime

# --- KONFIGURÁCIÓ ---
TOKEN = os.getenv("TOKEN")
# IDE ÍRD BE A CSATORNÁK ID-IT VESSZŐVEL ELVÁLASZTVA:
CHANNEL_IDS = [1457338828539957373] 
SEARCH_TERM = "lacoste" 
MAX_PRICE = 45000     

seen_ids = set()

class VintedBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        self.first_run = True

    async def setup_hook(self):
        self.monitor.start()

    def get_vinted_data(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Vinted lekérdezés indítása...")
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        headers = {"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Referer": "https://www.vinted.hu/"}
        url = f"https://www.vinted.hu/api/v2/catalog/items?search_text={SEARCH_TERM}&order=newest_first&countries[]=16&countries[]=24"
        try:
            self.session.cookies.clear()
            self.session.get("https://www.vinted.hu", headers=headers, timeout=10)
            res = self.session.get(url, headers=headers, timeout=10)
            return res
        except Exception as e: 
            print(f"❌ Hiba: {e}")
            return None

    async def on_ready(self):
        print(f"--- {self.user} ONLINE ÉS FIGYEL ---")

    @tasks.loop(seconds=115) # Alapidő: kb. 1.5 perc
    async def monitor(self):
        # Véletlenszerű várakozás (Anti-Ban Jitter)
        await asyncio.sleep(random.uniform(1, 15))
        
        if not TOKEN: return

        response = self.get_vinted_data()
        if response and response.status_code == 200:
            items = response.json().get('items', [])
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Sikeres válasz, {len(items)} termék ellenőrzése...")

            if self.first_run:
                for item in items: seen_ids.add(item.get('id'))
                self.first_run = False
                print(">>> Alapállapot kész. Mostantól jönnek az értesítések!")
                return

            for item in items[:10]:
                item_id = item.get('id')
                if item_id not in seen_ids:
                    raw_p = item.get('price')
                    price = float(raw_p.get('amount')) if isinstance(raw_p, dict) else float(raw_p)
                    
                    if price <= MAX_PRICE:
                        url = item.get('url')
                        currency = item.get('currency', 'HUF')
                        flag = "🇭🇺" if currency == "HUF" else "🇵🇱"
                        
                        brand = item.get('brand_title', 'Ismeretlen')
                        size = item.get('size_title', 'Nincs megadva')
                        status = item.get('status', 'Nincs infó')
                        rating = item.get('user', {}).get('feedback_reputation', 0)
                        stars = "⭐" * int(round(rating * 5)) if rating else "Nincs értékelés"

                        embed = discord.Embed(title=f"{flag} {item.get('title')}", url=url, color=0x00ff00)
                        embed.description = f"✨ **Állapot:** {status}"
                        
                        embed.add_field(name="📏 Méret", value=size, inline=True)
                        embed.add_field(name="🏷️ Márka", value=brand, inline=True)
                        embed.add_field(name="👤 Eladó", value=stars, inline=True)
                        embed.add_field(name="💰 Ár", value=f"**{price} {currency}**", inline=False)

                        if item.get('photo'): embed.set_image(url=item['photo'].get('url'))

                        view = View()
                        view.add_item(Button(label="Megtekintés", url=url, style=discord.ButtonStyle.link, emoji="🔗"))
                        view.add_item(Button(label="Vásárlás", url=url, style=discord.ButtonStyle.link, emoji="💸"))
                        
                        # KÜLDÉS MINDEN CSATORNÁBA
                        for channel_id in CHANNEL_IDS:
                            channel = self.get_channel(channel_id)
                            if channel:
                                try:
                                    await channel.send(embed=embed, view=view)
                                except Exception as e:
                                    print(f"Küldési hiba a(z) {channel_id} csatornán: {e}")
                        
                        print(f"🚀 ÚJ TALÁLAT BEKÜLDVE: {item.get('title')}")
                    seen_ids.add(item_id)
        else:
            status = response.status_code if response else "Nincs"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Vinted hiba (Kód: {status})")

intents = discord.Intents.default()
intents.message_content = True 
client = VintedBot(intents=intents)
client.run(TOKEN)
