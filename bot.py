"""
════════════════════════════════════════════════════════════════
ROBLOX AKTİFLİK TAKİP & YÖNETİM + DUYURU DISCORD BOTU
PART 1/4: YAPILANDIRMA, VERİTABANI & YARDIMCI FONKSİYONLAR
════════════════════════════════════════════════════════════════
✅ Subay kontrolü sadece Grup 6702531, Rank 10+
✅ Karaliste ve tasfiye tüm gruplarda çalışır
════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import aiohttp
import asyncio
from flask import Flask
from threading import Thread

# ═══════════════════════════════════════════════════════════════
# FLASK UYGULAMASI (UptimeRobot için)
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot çalışıyor! ✅", 200

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "online"}, 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ═══════════════════════════════════════════════════════════════
# BOT AYARLARI
# ═══════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ═══════════════════════════════════════════════════════════════
# YAPILANDIRMA - BURAYA KENDİ BİLGİLERİNİZİ YAZIN
# ═══════════════════════════════════════════════════════════════

# Discord Yetki Ayarları
YETKILI_ROL_IDS = [
    1264591330298826813,  # Örnek: Kurmay Rolü ID
    1461342472528465975,  # Örnek: Yönetici Rolü ID
]

# Duyuru Bot Rolleri
SUBAY_ROL_ID = os.getenv('SUBAY_ROL_ID', 'SUBAY_ROL_ID')
BOT_ROL_ID = os.getenv('BOT_ROL_ID', 'BOT_ROL_ID')

# Duyuru Kanal ID'leri
EGITIM_KANAL_ID = '1127312264718995629'
BRANS_KANAL_ID = '1128667321351815218'

# Roblox API Ayarları
ROBLOX_API_KEY_GROUPS = os.getenv('ROBLOX_API_KEY_GROUPS', 'YOUR_GROUP_API_KEY')
ROBLOX_API_KEY_DATASTORE = os.getenv('ROBLOX_API_KEY_DATASTORE', 'YOUR_DATASTORE_API_KEY')
UNIVERSE_ID = os.getenv('UNIVERSE_ID', 'YOUR_UNIVERSE_ID')
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE', 'YOUR_ROBLOSECURITY_COOKIE')  # ✅ YENİ: Legacy API için

ROBLOX_GRUP_LISTESI = [
    5836656, 35855814, 35856866, 17163069, 6702531,
    34055753, 32774293, 15222875, 7426468, 14014034,
    33709489, 15872878, 17163024, 32753497, 17167854, 17264057
]

# ✅ YENİ: Subay Kontrolü İçin Özel Grup Ayarları
SUBAY_KONTROL_GRUP_ID = 6702531  # Sadece bu grupta subay kontrolü yapılacak
SUBAY_MIN_RANK = 10  # Mülazım-ı Sani ve üstü (rank 10+)

# Rütbe Listesi
RUTBE_LISTESI = {
    "Acemi": 2, "Nefer": 3, "Nefer Birinci Sınıf": 4,
    "Onbaşı": 5, "Çavuş": 6, "Üstçavuş": 7, "Başçavuş": 9,
    "Mülazım-ı Sani": 10, "Mülazım-ı Evvel": 11, "Yüzbaşı": 12,
    "Kolağası": 13, "Binbaşı": 14, "Kaymakam": 15, "Miralay": 16,
    "Mirliva": 17, "Ferik": 18, "Ağa": 20, "Müşir": 21,
    "Serasker": 22, "Vezir-i Salis": 23, "Vezir-i Sani": 25,
    "Vezir-i Azam": 55, "Şehzade": 60, "Veliaht Şehzade": 65,
    "Padişah": 100, "Holder": 255
}

SUBAY_RUTBELERI = [
    "Mülazım-ı Sani", "Mülazım-ı Evvel", "Yüzbaşı", "Binbaşı",
    "Kaymakam", "Miralay", "Mirliva", "Ferik", "Ağa", "Müşir", "Serasker"
]

LOG_CHANNEL_ID = 1461362885337813004

# ═══════════════════════════════════════════════════════════════
# GLOBAL DEĞİŞKENLER
# ═══════════════════════════════════════════════════════════════

bekleyen_kullanicilar = {}
cooldowns = {}
savas_durumu = {
    'aktif': False, 'duraklatildi': False, 'basarili': 0,
    'basarisiz': 0, 'toplam': 0, 'simdiki': 0, 'kanal': None
}

# ═══════════════════════════════════════════════════════════════
# VERİTABANI YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

DATABASE_FILE = 'aktiflik_veritabani.json'
KARALISTE_FILE = 'karaliste.json'

def veritabani_yukle():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"players": [], "settings": {"minimum_hours": 5, "week_start_day": "monday"}}

def veritabani_kaydet(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def karaliste_yukle():
    if os.path.exists(KARALISTE_FILE):
        with open(KARALISTE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"blacklisted_users": []}

def karaliste_kaydet(data):
    with open(KARALISTE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def oyuncu_bul(roblox_username):
    db = veritabani_yukle()
    for i, player in enumerate(db['players']):
        if player['roblox_username'].lower() == roblox_username.lower():
            return player, i
    return None, None

# ═══════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════

def yetki_kontrol(ctx):
    kullanici_rol_ids = [role.id for role in ctx.author.roles]
    return any(rol_id in YETKILI_ROL_IDS for rol_id in kullanici_rol_ids)

def saniye_saat_donustur(saniye):
    saat = saniye // 3600
    dakika = (saniye % 3600) // 60
    return f"{saat}s {dakika}d"

def renk_bul(toplam_saat):
    if toplam_saat >= 7:
        return "🟢"
    elif toplam_saat >= 5:
        return "🟡"
    else:
        return "🔴"

# ═══════════════════════════════════════════════════════════════
# ROBLOX API FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════

async def roblox_kullanici_id_al(username):
    url = "https://users.roblox.com/v1/usernames/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"usernames": [username]}) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]['id']
    return None

# Roblox Cookie (Legacy API için gerekli - Grup sahibi olmasanız da çalışır)
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE', 'YOUR_ROBLOSECURITY_COOKIE')

async def roblox_rutbe_degistir(user_id, rank_id, group_id):
    """
    Legacy Groups API kullanarak rütbe değiştir
    NOT: Grup sahibi olmadan da çalışır, sadece yeterli yetkiniz olması lazım
    """
    
    async with aiohttp.ClientSession() as session:
        # 1. CSRF Token Al
        csrf_url = "https://auth.roblox.com/v2/logout"
        headers = {"Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}"}
        
        csrf_token = None
        async with session.post(csrf_url, headers=headers) as response:
            csrf_token = response.headers.get('x-csrf-token')
        
        if not csrf_token:
            return False, "CSRF token alınamadı! Cookie'nizi kontrol edin."
        
        # 2. Gruptaki rolleri al ve rank_id'ye karşılık gelen role ID'yi bul
        roles_url = f"https://groups.roblox.com/v1/groups/{group_id}/roles"
        async with session.get(roles_url) as response:
            if response.status != 200:
                return False, f"Grup rolleri alınamadı (Status: {response.status})"
            
            roles_data = await response.json()
            roles = roles_data.get('roles', [])
            
            # Rank numarasına göre role ID bul
            role_id = None
            for role in roles:
                if role.get('rank') == rank_id:
                    role_id = role.get('id')
                    break
            
            if not role_id:
                available_ranks = ", ".join([str(r.get('rank')) for r in roles])
                return False, f"Grup {group_id}'de Rank {rank_id} bulunamadı! Mevcut ranklar: {available_ranks}"
        
        # 3. Rütbe Değiştir (roleId kullan, rank değil!)
        url = f"https://groups.roblox.com/v1/groups/{group_id}/users/{user_id}"
        headers = {
            "Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}",
            "X-CSRF-TOKEN": csrf_token,
            "Content-Type": "application/json"
        }
        payload = {"roleId": role_id}  # rank_id değil, role_id!
        
        async with session.patch(url, headers=headers, json=payload) as response:
            if response.status == 200:
                return True, "Başarılı"
            else:
                error_text = await response.text()
                return False, f"Hata: {error_text}"

async def roblox_mevcut_rutbe_al(user_id):
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                for group in data.get('data', []):
                    if group['group']['id'] in ROBLOX_GRUP_LISTESI:
                        return group['role']['name']
    return "Bilinmiyor"

async def roblox_gruptan_cikar(user_id, group_id):
    url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships/{user_id}"
    headers = {"x-api-key": ROBLOX_API_KEY_GROUPS}
    
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as response:
            return response.status == 200

async def roblox_haftalik_aktiflik_al(user_id):
    datastore_name = "PlayerSessions_v2"
    entry_key = str(user_id)
    url = f"https://apis.roblox.com/datastores/v1/universes/{UNIVERSE_ID}/standard-datastores/datastore/entries/entry"
    headers = {"x-api-key": ROBLOX_API_KEY_DATASTORE}
    params = {"datastoreName": datastore_name, "entryKey": entry_key}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict):
                        weekly_seconds = data.get('weeklySeconds', 0)
                        return True, weekly_seconds
                    else:
                        return False, "Veri formatı hatalı"
                elif response.status == 404:
                    return True, 0
                else:
                    error_text = await response.text()
                    return False, f"API Hatası ({response.status}): {error_text}"
    except Exception as e:
        return False, f"Bağlantı hatası: {str(e)}"

async def roblox_toplam_aktiflik_al(user_id):
    datastore_name = "PlayerPlayTime_v2"
    entry_key = str(user_id)
    url = f"https://apis.roblox.com/datastores/v1/universes/{UNIVERSE_ID}/standard-datastores/datastore/entries/entry"
    headers = {"x-api-key": ROBLOX_API_KEY_DATASTORE}
    params = {"datastoreName": datastore_name, "entryKey": entry_key}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    total_seconds = await response.json()
                    return True, int(total_seconds)
                elif response.status == 404:
                    return True, 0
                else:
                    error_text = await response.text()
                    return False, f"API Hatası ({response.status}): {error_text}"
    except Exception as e:
        return False, f"Bağlantı hatası: {str(e)}"

async def roblox_toplu_aktiflik_al(user_ids):
    results = {}
    for user_id in user_ids:
        success, data = await roblox_haftalik_aktiflik_al(user_id)
        if success:
            results[user_id] = data
        else:
            results[user_id] = 0
            print(f"⚠️ Aktiflik alınamadı (UserID: {user_id}): {data}")
        await asyncio.sleep(0.1)
    return results

# ✅ YENİ FONKSİYON: Subay Kontrolü
async def subay_mi_kontrol(user_id):
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for group in data.get('data', []):
                        if group['group']['id'] == SUBAY_KONTROL_GRUP_ID:
                            rank = group['role']['rank']
                            rank_name = group['role']['name']
                            
                            if rank >= SUBAY_MIN_RANK:
                                return True, rank, rank_name
                            else:
                                return False, rank, rank_name
                    
                    return False, 0, "Grupta Değil"
    except Exception as e:
        print(f"Subay kontrolü hatası (UserID: {user_id}): {e}")
        return False, 0, "Hata"
    
    return False, 0, "Bilinmiyor"

# ═══════════════════════════════════════════════════════════════
# DUYURU MESAJ FORMATLARI
# ═══════════════════════════════════════════════════════════════

class Formatlar:
    @staticmethod
    def egitimduyuru(host, co, saat):
        co_text = 'Yok' if co.lower() == 'yok' else co
        return f"""📚 **EĞİTİM DUYURUSU**

**Host:** {host}
**Co:** {co_text}
**Tür:** Genel
**Saat:** {saat}
**Yer:** STS
**Tag:** <@&1254785306343772271>

https://www.roblox.com/games/11734871771/YEN-Osmanl-Asker-Oyun"""

    @staticmethod
    def bransalim(host, co, brans, saat, sartlar=None):
        co_text = '-' if co.lower() == 'yok' else co
        mesaj = f"""🎯 **BRANŞ ALIM DUYURUSU**

**Host:** {host}
**Co:** {co_text}
**Branş:** {brans}
**Saat:** {saat}
**Tag:** <@&1254785306343772271>

https://www.roblox.com/games/11734871771/YEN-Ottoman-Army-Simulator"""
        if sartlar:
            mesaj += f"\n\n**Şartlar:**\n{sartlar}"
        return mesaj

    @staticmethod
    def savas_dm():
        return """@everyone
# Savaş başlıyor Oyuna giriş yap! / Battle is starting now join up!
https://discord.com/channels/1127292848044245133/1200486502870814810
https://www.roblox.com/games/11734871771/YEN-Osmanl-Asker-Oyunu"""

# ═══════════════════════════════════════════════════════════════
# BEKLEME MESAJI YÖNETİCİSİ
# ═══════════════════════════════════════════════════════════════

async def handle_bekleyen_mesaj(message):
    user_data = bekleyen_kullanicilar.get(message.author.id)
    if not user_data:
        return

    adim = user_data['adim']

    if adim == 'kanal':
        kanal_id = message.content.strip()
        try:
            kanal = await bot.fetch_channel(int(kanal_id))
            bekleyen_kullanicilar[message.author.id] = {'adim': 'mesaj', 'kanal': kanal}
            await message.reply(f'✅ Kanal seçildi: {kanal.mention}\n📝 Şimdi göndermek istediğiniz mesajı yazın:')
        except Exception as e:
            await message.reply('❌ Geçersiz kanal ID! Lütfen tekrar deneyin:')
            print(f"Kanal fetch hatası: {e}")
        return

    if adim == 'mesaj':
        kanal = user_data['kanal']
        try:
            await kanal.send(message.content)
            await message.reply(f'✅ Mesaj başarıyla {kanal.mention} kanalına gönderildi!')
        except Exception as e:
            await message.reply(f'❌ Mesaj gönderilemedi: {str(e)}')
        del bekleyen_kullanicilar[message.author.id]
        return

    if adim == 'brans_sartlar':
        data = user_data['data']
        sartlar = None if message.content.lower() in ['hayır', 'yok', 'hayir'] else message.content
        kanal = bot.get_channel(int(data['kanal']))
        
        try:
            await message.delete()
        except Exception as e:
            print(f'Kullanıcı mesajı silinemedi: {e}')
        
        try:
            soru_mesaji_id = user_data.get('soru_mesaji_id')
            if soru_mesaji_id:
                soru_mesaji = await kanal.fetch_message(soru_mesaji_id)
                await soru_mesaji.delete()
        except Exception as e:
            print(f'Soru mesajı silinemedi: {e}')
        
        yeni_mesaj = Formatlar.bransalim(data['host'], data['co'], data['brans'], data['saat'], sartlar)
        await kanal.send(yeni_mesaj)
        cooldowns[data['cooldownKey']] = datetime.now()
        del bekleyen_kullanicilar[message.author.id]
        return

# ═══════════════════════════════════════════════════════════════
# BOT EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print('═' * 80)
    print('✅ ROBLOX AKTİFLİK TAKİP & YÖNETİM + DUYURU BOTU BAŞLATILDI')
    print('═' * 80)
    print(f'Bot Adı: {bot.user.name} ({bot.user.id})')
    print(f'Sunucu Sayısı: {len(bot.guilds)}')
    print(f'Kullanıcı Sayısı: {len(bot.users)}')
    
    db = veritabani_yukle()
    karaliste_db = karaliste_yukle()
    
    print(f'Kayıtlı Oyuncu: {len(db.get("players", []))}')
    print(f'Karalistedekiler: {len(karaliste_db.get("blacklisted_users", []))}')
    print('─' * 80)
    print(f'✅ Subay Kontrolü: Grup {SUBAY_KONTROL_GRUP_ID}, Rank {SUBAY_MIN_RANK}+')
    print('═' * 80)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id in bekleyen_kullanicilar:
        await handle_bekleyen_mesaj(message)
        return
    await bot.process_commands(message)

# ════════════════════════════════════════════════════════════════
# PART 1 SONU
# ════════════════════════════════════════════════════════════════
"""
════════════════════════════════════════════════════════════════
PART 2/4: AKTİFLİK KOMUTLARI
════════════════════════════════════════════════════════════════
Bu dosyayı Part 1'in sonuna ekleyin
════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - AKTİFLİK SORGULAMA
# ═══════════════════════════════════════════════════════════════

@bot.command(name='komutlar')
async def komutlar_listesi(ctx):
    """Tüm komutları listele"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    embed = discord.Embed(
        title="🎮 AKTİFLİK & YÖNETİM & DUYURU KOMUTLARI",
        description="Aşağıdaki komutları kullanabilirsiniz:",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    
    embed.add_field(
        name="📊 Aktiflik Sorgulama",
        value=(
            "**`!logs all`** - Tüm subayların haftalık aktiflik listesi\n"
            "**`!logs <roblox_isim>`** - Belirli oyuncunun detaylı raporu\n"
            "**`!aktiflik-sorgula <roblox_isim>`** - API'den direkt sorgula\n"
            "**`!haftalik-rapor`** - Detaylı haftalık rapor"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏖️ İzin Yönetimi",
        value=(
            "**`!inaktiflikizin <roblox_isim>`** - Haftalık izin ver\n"
            "**`!izinkaldır <roblox_isim>`** - İzni kaldır"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⭐ Rütbe Yönetimi",
        value=(
            "**`!tasfiye <roblox_isim> <yeni_rutbe>`** - Rütbe değiştir\n"
            "**`!rutbeler`** - Kullanılabilir rütbeleri listele"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🚫 Karaliste Yönetimi",
        value=(
            "**`!karaliste @discord <roblox_isim> <sebep>`** - Karalisteye al\n"
            "**`!karalistesorgula <kullanici_adi>`** - Karaliste sorgula"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📢 Duyuru Komutları",
        value=(
            "**`!egitimduyuru <host> <co/yok> <saat>`** - Eğitim duyurusu\n"
            "**`!bransalim <host> <co/yok> <branş> <saat>`** - Branş alım\n"
            "**`!duyuru`** - Özel kanal mesajı"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Savaş Sistemi",
        value=(
            "**`!savas`** - Aktif üyelere savaş duyurusu\n"
            "**`!durum`** - Savaş durumunu göster\n"
            "**`!dur`** - Savaşı duraklat\n"
            "**`!devam`** - Savaşa devam et\n"
            "**`!iptal`** - Savaşı iptal et"
        ),
        inline=False
    )

    embed.add_field(
        name="📨 DM Gönderimi",
        value=(
            "**`!dmgonder aktif`** - Online/idle/dnd olan herkese DM at\n"
            "**`!dmgonder herkes`** - Tüm üyelere DM at\n"
            "**`!dmgonder rol @Rol`** - Belirli role sahip herkese DM at\n"
            "**`!dmdur`** - DM gönderimini duraklat\n"
            "**`!dmdevam`** - DM gönderimini devam ettir\n"
            "**`!dmiptal`** - Devam eden DM gönderimini iptal et"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 Diğer",
        value=(
            "**`!cooldownkaldir <komut>`** - Cooldown kaldır\n"
            "**`!ping`** - Bot gecikmesini göster\n"
            "**`!api-test`** - API bağlantısını test et"
        ),
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Önemli Bilgi",
        value=f"Subay kontrolü: **Grup {SUBAY_KONTROL_GRUP_ID}, Rank {SUBAY_MIN_RANK}+**",
        inline=False
    )
    
    embed.set_footer(text=f"Sorguyu yapan: {ctx.author.name}")
    await ctx.send(embed=embed)


@bot.command(name='logs')
async def logs(ctx, *, hedef: str = None):
    """Aktiflik loglarını göster"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not hedef:
        await ctx.send(
            "❌ Kullanım:\n"
            "`!logs all` - Tüm subayların listesi\n"
            "`!logs <roblox_isim>` - Belirli oyuncunun detayları"
        )
        return
    
    db = veritabani_yukle()
    
    if hedef.lower() == 'all':
        await ctx.reply('🔍 Subaylar taranıyor... (Bu biraz zaman alabilir)')
        
        subaylar = []
        
        for player in db.get('players', []):
            roblox_id = player.get('roblox_id')
            roblox_username = player.get('roblox_username')
            
            if not roblox_id or not roblox_username:
                continue
            
            is_officer, rank, rank_name = await subay_mi_kontrol(roblox_id)
            
            if is_officer:
                weekly_data = player.get('weekly_data', {})
                total_seconds = weekly_data.get('total_seconds', 0)
                on_leave = weekly_data.get('on_leave', False)
                
                subaylar.append({
                    'roblox_username': roblox_username,
                    'rank': rank,
                    'rank_name': rank_name,
                    'total_seconds': total_seconds,
                    'on_leave': on_leave
                })
            
            await asyncio.sleep(0.1)
        
        if not subaylar:
            await ctx.send("❌ Kayıtlı subay bulunamadı!")
            return
        
        subaylar.sort(key=lambda x: x['total_seconds'])
        
        embed = discord.Embed(
            title="📊 HAFTALIK AKTİFLİK RAPORU",
            description=f"Toplam {len(subaylar)} subay (Grup: {SUBAY_KONTROL_GRUP_ID}, Rank {SUBAY_MIN_RANK}+)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        rapor_metni = ""
        for player in subaylar:
            toplam_saniye = player['total_seconds']
            toplam_saat = toplam_saniye / 3600
            izinli = player['on_leave']
            
            renk_emoji = renk_bul(toplam_saat)
            izin_emoji = " 🏖️" if izinli else ""
            
            rapor_metni += (
                f"{renk_emoji} **{player['roblox_username']}** "
                f"({player['rank_name']}) - "
                f"{saniye_saat_donustur(toplam_saniye)}{izin_emoji}\n"
            )
        
        if len(rapor_metni) > 1024:
            parts = [rapor_metni[i:i+1024] for i in range(0, len(rapor_metni), 1024)]
            for i, part in enumerate(parts):
                embed.add_field(
                    name=f"📋 Liste ({i+1}/{len(parts)})",
                    value=part,
                    inline=False
                )
        else:
            embed.add_field(name="📋 Aktiflik Listesi", value=rapor_metni, inline=False)
        
        embed.add_field(
            name="📌 Açıklama",
            value=(
                "🟢 Yeterli (7+ saat) | 🟡 Sınırda (5-7 saat) | 🔴 Yetersiz (<5 saat)\n"
                f"ℹ️ Sadece **Grup {SUBAY_KONTROL_GRUP_ID}** - **Rank {SUBAY_MIN_RANK}+** gösteriliyor"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Sorguyu yapan: {ctx.author.name}")
        await ctx.send(embed=embed)
        return
    
    # TEK OYUNCU
    player, index = oyuncu_bul(hedef)
    
    if not player:
        await ctx.send(f"❌ `{hedef}` adlı oyuncu veritabanında bulunamadı!")
        return
    
    toplam_saniye = player.get('weekly_data', {}).get('total_seconds', 0)
    oturum_sayisi = len(player.get('weekly_data', {}).get('sessions', []))
    izinli = player.get('weekly_data', {}).get('on_leave', False)
    
    toplam_saat = toplam_saniye / 3600
    renk_emoji = renk_bul(toplam_saat)
    
    if toplam_saat >= 7:
        renk = discord.Color.green()
        durum = "Yeterli ✅"
    elif toplam_saat >= 5:
        renk = discord.Color.gold()
        durum = "Sınırda ⚠️"
    else:
        renk = discord.Color.red()
        durum = "Yetersiz ❌"
    
    embed = discord.Embed(
        title=f"📊 {player['roblox_username']} - Detaylı Rapor",
        color=renk,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="👤 Bilgiler",
        value=(
            f"**Roblox Adı:** {player['roblox_username']}\n"
            f"**Rütbe:** {player.get('rank', 'Bilinmiyor')}\n"
            f"**Durum:** {durum}"
        ),
        inline=False
    )
    
    embed.add_field(
        name=f"{renk_emoji} Haftalık Aktiflik",
        value=(
            f"**Toplam Süre:** {saniye_saat_donustur(toplam_saniye)}\n"
            f"**Giriş Sayısı:** {oturum_sayisi} kez\n"
            f"**İzinli:** {'✅ Evet' if izinli else '❌ Hayır'}"
        ),
        inline=False
    )
    
    oturumlar = player.get('weekly_data', {}).get('sessions', [])
    if oturumlar:
        son_oturumlar = oturumlar[-5:]
        oturum_metni = ""
        
        for oturum in son_oturumlar:
            tarih = oturum.get('date', 'Bilinmiyor')
            giris = oturum.get('login_time', '00:00:00')
            cikis = oturum.get('logout_time', '00:00:00')
            sure = oturum.get('duration', 0)
            
            oturum_metni += (
                f"📅 **{tarih}** - {giris} → {cikis} "
                f"({saniye_saat_donustur(sure)})\n"
            )
        
        embed.add_field(
            name="📜 Son Oturumlar",
            value=oturum_metni if oturum_metni else "Oturum kaydı yok",
            inline=False
        )
    
    embed.set_footer(text=f"Sorguyu yapan: {ctx.author.name}")
    await ctx.send(embed=embed)


@bot.command(name='inaktiflikizin')
async def inaktiflik_izin(ctx, *, roblox_username: str = None):
    """Oyuncuya haftalık izin ver"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not roblox_username:
        await ctx.send("❌ Kullanım: `!inaktiflikizin <roblox_isim>`")
        return
    
    player, index = oyuncu_bul(roblox_username)
    
    if not player:
        await ctx.send(f"❌ `{roblox_username}` adlı oyuncu bulunamadı!")
        return
    
    if player.get('weekly_data', {}).get('on_leave', False):
        await ctx.send(f"⚠️ **{roblox_username}** zaten izinli durumda!")
        return
    
    db = veritabani_yukle()
    if 'weekly_data' not in db['players'][index]:
        db['players'][index]['weekly_data'] = {
            'total_seconds': 0,
            'sessions': [],
            'on_leave': False
        }
    
    db['players'][index]['weekly_data']['on_leave'] = True
    veritabani_kaydet(db)
    
    embed = discord.Embed(
        title="✅ İZİN VERİLDİ",
        description=f"**{roblox_username}** bu hafta için izinli olarak işaretlendi.",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="ℹ️ Bilgi",
        value="Oyuncu bu hafta aktiflik kontrolünden muaf tutulacak.",
        inline=False
    )
    
    embed.set_footer(text=f"İşlemi yapan: {ctx.author.name}")
    await ctx.send(embed=embed)


@bot.command(name='izinkaldır')
async def izin_kaldir(ctx, *, roblox_username: str = None):
    """Oyuncunun iznini kaldır"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not roblox_username:
        await ctx.send("❌ Kullanım: `!izinkaldır <roblox_isim>`")
        return
    
    player, index = oyuncu_bul(roblox_username)
    
    if not player:
        await ctx.send(f"❌ `{roblox_username}` adlı oyuncu bulunamadı!")
        return
    
    if not player.get('weekly_data', {}).get('on_leave', False):
        await ctx.send(f"⚠️ **{roblox_username}** zaten izinli değil!")
        return
    
    db = veritabani_yukle()
    db['players'][index]['weekly_data']['on_leave'] = False
    veritabani_kaydet(db)
    
    embed = discord.Embed(
        title="✅ İZİN KALDIRILDI",
        description=f"**{roblox_username}** artık izinli değil.",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="ℹ️ Bilgi",
        value="Oyuncu artık aktiflik kontrolüne dahil olacak.",
        inline=False
    )
    
    embed.set_footer(text=f"İşlemi yapan: {ctx.author.name}")
    await ctx.send(embed=embed)

# ════════════════════════════════════════════════════════════════
# PART 2 SONU
# ════════════════════════════════════════════════════════════════
"""
════════════════════════════════════════════════════════════════
PART 3/4: RÜTBE, KARALİSTE & DUYURU KOMUTLARI
════════════════════════════════════════════════════════════════
Bu dosyayı Part 2'nin sonuna ekleyin
════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - RÜTBE YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

@bot.command(name='tasfiye')
async def tasfiye(ctx, grup_veya_hepsi: str = None, roblox_username: str = None, rank_id: str = None):
    """
    Oyuncunun rütbesini değiştir - Rank ID ile
    Kullanım: !tasfiye <grup_id veya 'hepsi'> <roblox_isim> <rank_numarası>
    Örnek: !tasfiye 6702531 EmirVonDietricyan 2
    Örnek: !tasfiye hepsi EmirVonDietricyan 2
    """
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not grup_veya_hepsi or not roblox_username or not rank_id:
        await ctx.send(
            "❌ **Kullanım:** `!tasfiye <grup_id veya 'hepsi'> <roblox_isim> <rank_numarası>`\n\n"
            "**Örnekler:**\n"
            "• `!tasfiye 6702531 EmirVonDietricyan 2` - Sadece bir grupta\n"
            "• `!tasfiye hepsi EmirVonDietricyan 2` - Tüm gruplarda\n\n"
            "**Rank numaraları grupta ne ise o olmalı** (2=Er, 3=Onbaşı vs.)"
        )
        return
    
    # Rank ID'yi sayıya çevir
    try:
        rank_id = int(rank_id)
    except:
        await ctx.send("❌ Rank numarası geçerli bir sayı olmalı!")
        return
    
    # Grup ID'yi belirle
    if grup_veya_hepsi.lower() == "hepsi":
        grup_listesi = ROBLOX_GRUP_LISTESI
        islem_tipi = "TÜM GRUPLARDA"
    else:
        try:
            grup_id = int(grup_veya_hepsi)
            grup_listesi = [grup_id]
            islem_tipi = f"GRUP {grup_id}'de"
        except:
            await ctx.send("❌ Grup ID geçerli bir sayı olmalı veya 'hepsi' yazın!")
            return
    
    # Roblox kullanıcı ID'sini al
    islem_mesaji = await ctx.send(f"⏳ `{roblox_username}` için Roblox bilgileri çekiliyor...")
    
    roblox_user_id = await roblox_kullanici_id_al(roblox_username)
    
    if not roblox_user_id:
        await islem_mesaji.edit(content=f"❌ `{roblox_username}` adlı oyuncu Roblox'ta bulunamadı!")
        return
    
    eski_rutbe = await roblox_mevcut_rutbe_al(roblox_user_id)
    await islem_mesaji.edit(content=f"⏳ `{roblox_username}` için {islem_tipi} rütbe değiştirme başlatıldı...")
    
    basarili_gruplar = []
    basarisiz_gruplar = []
    
    for group_id in grup_listesi:
        basarili, mesaj = await roblox_rutbe_degistir(roblox_user_id, rank_id, group_id)
        
        if basarili:
            basarili_gruplar.append(group_id)
        else:
            basarisiz_gruplar.append((group_id, mesaj))
        
        await asyncio.sleep(0.5)  # Rate limit için bekle
    
    # Sonuç embed'i oluştur
    if basarili_gruplar:
        embed = discord.Embed(
            title="✅ RÜTBE DEĞİŞTİRME TAMAMLANDI",
            description=f"**{roblox_username}** için rütbe değiştirildi.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Oyuncu Bilgileri",
            value=f"**Roblox:** {roblox_username}\n**User ID:** {roblox_user_id}\n**Eski Rütbe:** {eski_rutbe}",
            inline=False
        )
        
        embed.add_field(
            name="⭐ Yeni Rank",
            value=f"**Rank ID:** {rank_id}",
            inline=False
        )
        
        if len(basarili_gruplar) > 0:
            gruplar_text = "\n".join([f"• Grup {g}" for g in basarili_gruplar])
            embed.add_field(
                name=f"✅ Başarılı ({len(basarili_gruplar)} grup)",
                value=gruplar_text[:1024],
                inline=False
            )
        
        if basarisiz_gruplar:
            hatalar_text = "\n".join([f"• Grup {g}: {m[:50]}..." for g, m in basarisiz_gruplar[:5]])
            embed.add_field(
                name=f"❌ Başarısız ({len(basarisiz_gruplar)} grup)",
                value=hatalar_text[:1024],
                inline=False
            )
        
        embed.set_footer(text=f"İşlemi yapan: {ctx.author.name}")
        
        await islem_mesaji.delete()
        await ctx.send(embed=embed)
    else:
        hata_mesaji = "❌ Hiçbir grupta rütbe değiştirilemedi!\n\n"
        for g, m in basarisiz_gruplar[:3]:
            hata_mesaji += f"**Grup {g}:** {m}\n"
        
        await islem_mesaji.edit(content=hata_mesaji)
    
    # Veritabanındaysa güncelle
    player, index = oyuncu_bul(roblox_username)
    if player and index is not None:
        db = veritabani_yukle()
        db['players'][index]['rank'] = f"Rank {rank_id}"
        veritabani_kaydet(db)


@bot.command(name='rutbeler')
async def rutbeler_listesi(ctx):
    """Kullanılabilir rütbeleri listele"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    embed = discord.Embed(
        title="⭐ KULLANILABİLİR RÜTBELER",
        description="Tasfiye komutunda kullanabileceğiniz rütbeler:",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    rutbe_metni = ""
    for rutbe, rank_id in RUTBE_LISTESI.items():
        rutbe_metni += f"**{rutbe}** (Rank ID: {rank_id})\n"
    
    embed.add_field(name="📋 Rütbe Listesi", value=rutbe_metni, inline=False)
    embed.add_field(name="💡 Kullanım", value="Örnek: `!tasfiye MehmetSubay Er`", inline=False)
    embed.set_footer(text=f"Sorguyu yapan: {ctx.author.name}")
    
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - KARALİSTE YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

@bot.command(name='karaliste')
async def karaliste_komut(ctx, discord_kullanici: discord.Member = None, roblox_username: str = None, *, sebep: str = None):
    """Kullanıcıyı karalisteye al (TÜM GRUPLARDA)"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not discord_kullanici or not roblox_username or not sebep:
        await ctx.send(
            "❌ Kullanım: `!karaliste @discord_kullanici <roblox_isim> <sebep>`\n"
            "Örnek: `!karaliste @Mehmet#1234 MehmetRBLX Trolling`"
        )
        return
    
    onay_embed = discord.Embed(
        title="⚠️ KARALİSTE ONAY GEREKLİ",
        description=(
            f"**{discord_kullanici.mention}** kullanıcısını karalisteye almak üzeresiniz!\n\n"
            f"**Roblox:** {roblox_username}\n**Sebep:** {sebep}\n\n"
            f"**Devam etmek istediğinize emin misiniz?**"
        ),
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    onay_mesaji = await ctx.send(embed=onay_embed)
    await onay_mesaji.add_reaction("✅")
    await onay_mesaji.add_reaction("❌")
    
    def check(reaction, user):
        return (user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == onay_mesaji.id)
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        if str(reaction.emoji) == "❌":
            await onay_mesaji.edit(embed=discord.Embed(
                title="❌ İşlem İptal Edildi",
                description="Karaliste işlemi iptal edildi.",
                color=discord.Color.orange()
            ))
            await onay_mesaji.clear_reactions()
            return
    except:
        await onay_mesaji.edit(embed=discord.Embed(
            title="⏱️ Zaman Aşımı",
            description="İşlem zaman aşımına uğradı.",
            color=discord.Color.orange()
        ))
        await onay_mesaji.clear_reactions()
        return
    
    await onay_mesaji.clear_reactions()
    await onay_mesaji.edit(content="⏳ Karaliste işlemi başlatıldı...")
    
    banlanan_sunucu_sayisi = 0
    for guild in bot.guilds:
        try:
            await guild.ban(
                discord_kullanici,
                reason=f"Karaliste - Yetkili: {ctx.author} - Sebep: {sebep}",
                delete_message_days=7
            )
            banlanan_sunucu_sayisi += 1
        except:
            pass
    
    roblox_user_id = await roblox_kullanici_id_al(roblox_username)
    
    cikarilan_grup_sayisi = 0
    if roblox_user_id:
        for group_id in ROBLOX_GRUP_LISTESI:
            if await roblox_gruptan_cikar(roblox_user_id, group_id):
                cikarilan_grup_sayisi += 1
    
    karaliste_db = karaliste_yukle()
    karaliste_kayit = {
        "discord_id": str(discord_kullanici.id),
        "discord_username": str(discord_kullanici),
        "roblox_username": roblox_username,
        "roblox_id": roblox_user_id,
        "sebep": sebep,
        "yetkili_discord_id": str(ctx.author.id),
        "yetkili_ad": str(ctx.author),
        "tarih": datetime.now().isoformat()
    }
    
    karaliste_db["blacklisted_users"].append(karaliste_kayit)
    karaliste_kaydet(karaliste_db)
    
    sonuc_embed = discord.Embed(
        title="✅ KARALİSTE İŞLEMİ TAMAMLANDI",
        description=f"**{discord_kullanici}** karalisteye alındı.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    sonuc_embed.add_field(
        name="📊 İşlem Sonuçları",
        value=(
            f"**Discord Banları:** {banlanan_sunucu_sayisi}/{len(bot.guilds)} sunucu\n"
            f"**Roblox Çıkarımları:** {cikarilan_grup_sayisi}/{len(ROBLOX_GRUP_LISTESI)} grup"
        ),
        inline=False
    )
    
    sonuc_embed.set_footer(text=f"İşlemi yapan: {ctx.author.name}")
    await onay_mesaji.edit(content=None, embed=sonuc_embed)


@bot.command(name='karalistesorgula')
async def karaliste_sorgula(ctx, *, kullanici_adi: str = None):
    """Karaliste sorgula"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not kullanici_adi:
        await ctx.send("❌ Kullanım: `!karalistesorgula <roblox_isim veya discord_isim>`")
        return
    
    karaliste_db = karaliste_yukle()
    
    bulunan_kayitlar = []
    for kayit in karaliste_db["blacklisted_users"]:
        if (kullanici_adi.lower() in kayit["roblox_username"].lower() or 
            kullanici_adi.lower() in kayit["discord_username"].lower()):
            bulunan_kayitlar.append(kayit)
    
    if not bulunan_kayitlar:
        await ctx.send(f"❌ `{kullanici_adi}` için karaliste kaydı bulunamadı.")
        return
    
    for kayit in bulunan_kayitlar[:3]:
        embed = discord.Embed(
            title="🚫 KARALİSTE KAYDI",
            color=discord.Color.red(),
            timestamp=datetime.fromisoformat(kayit["tarih"])
        )
        
        embed.add_field(
            name="👤 Kullanıcı",
            value=(
                f"**Discord:** {kayit['discord_username']}\n"
                f"**Roblox:** {kayit['roblox_username']}\n"
                f"**Sebep:** {kayit['sebep']}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📋 İşlem",
            value=f"**Yetkili:** {kayit['yetkili_ad']}\n**Tarih:** {datetime.fromisoformat(kayit['tarih']).strftime('%d.%m.%Y %H:%M')}",
            inline=False
        )
        
        await ctx.send(embed=embed)

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - DUYURU SİSTEMİ
# ═══════════════════════════════════════════════════════════════

@bot.command(name='duyuru')
async def duyuru(ctx):
    """Belirli bir kanala mesaj gönder"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return
    
    bekleyen_kullanicilar[ctx.author.id] = {'adim': 'kanal'}
    await ctx.reply('📢 Hangi kanala mesaj göndermek istiyorsunuz? Kanal ID\'sini yazın:')


@bot.command(name='egitimduyuru')
async def egitimduyuru(ctx, host: str = None, co: str = None, saat: str = None):
    """Eğitim duyurusu gönder"""
    if not any(str(role.id) == SUBAY_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için gerekli role sahip değilsiniz!')
        return

    if str(ctx.channel.id) != EGITIM_KANAL_ID:
        await ctx.reply(f'❌ Bu komutu sadece <#{EGITIM_KANAL_ID}> kanalında kullanabilirsiniz!')
        return

    cooldown_key = f'{ctx.author.id}-egitimduyuru'
    son_kullanim = cooldowns.get(cooldown_key)
    simdiki_zaman = datetime.now()
    cooldown_sure = timedelta(minutes=15)

    if son_kullanim and (simdiki_zaman - son_kullanim) < cooldown_sure:
        kalan_sure = int((cooldown_sure - (simdiki_zaman - son_kullanim)).total_seconds() / 60) + 1
        await ctx.reply(f'⏰ Bu komutu tekrar kullanabilmek için {kalan_sure} dakika beklemelisiniz!')
        return

    if not all([host, co, saat]):
        await ctx.reply('❌ Kullanım: `!egitimduyuru Host Co/yok Saat`\nÖrnek: `!egitimduyuru AhmetBey yok 20:00`')
        return

    yeni_mesaj = Formatlar.egitimduyuru(host, co, saat)

    try:
        await ctx.message.delete()
    except Exception as e:
        print(f'Mesaj silinemedi: {e}')

    await ctx.send(yeni_mesaj)
    cooldowns[cooldown_key] = simdiki_zaman


@bot.command(name='bransalim')
async def bransalim(ctx, host: str = None, co: str = None, brans: str = None, saat: str = None):
    """Branş alım duyurusu gönder"""
    if not any(str(role.id) == SUBAY_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için gerekli role sahip değilsiniz!')
        return

    if str(ctx.channel.id) != BRANS_KANAL_ID:
        await ctx.reply(f'❌ Bu komutu sadece <#{BRANS_KANAL_ID}> kanalında kullanabilirsiniz!')
        return

    cooldown_key = f'{ctx.author.id}-bransalim'
    son_kullanim = cooldowns.get(cooldown_key)
    simdiki_zaman = datetime.now()
    cooldown_sure = timedelta(minutes=15)

    if son_kullanim and (simdiki_zaman - son_kullanim) < cooldown_sure:
        kalan_sure = int((cooldown_sure - (simdiki_zaman - son_kullanim)).total_seconds() / 60) + 1
        await ctx.reply(f'⏰ Bu komutu tekrar kullanabilmek için {kalan_sure} dakika beklemelisiniz!')
        return

    if not all([host, co, brans, saat]):
        await ctx.reply('❌ Kullanım: `!bransalim Host Co/yok Branş Saat`\nÖrnek: `!bransalim AhmetBey yok Piyade 20:00`')
        return

    try:
        await ctx.message.delete()
    except Exception as e:
        print(f'Mesaj silinemedi: {e}')

    soru_mesaji = await ctx.send(f'{ctx.author.mention} 📋 Şartlar olacak mı? Varsa şartları yazın, yoksa "hayır" veya "yok" yazın:')

    bekleyen_kullanicilar[ctx.author.id] = {
        'adim': 'brans_sartlar',
        'data': {
            'host': host,
            'co': co,
            'brans': brans,
            'saat': saat,
            'kanal': str(ctx.channel.id),
            'cooldownKey': cooldown_key
        },
        'soru_mesaji_id': soru_mesaji.id
    }


@bot.command(name='cooldownkaldir')
async def cooldownkaldir(ctx, komut: str = None):
    """Tüm kullanıcıların cooldown'unu kaldır"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return
    
    if not komut:
        await ctx.reply('❌ Kullanım: `!cooldownkaldir egitimduyuru/bransalim`')
        return
    
    if komut not in ['egitimduyuru', 'bransalim']:
        await ctx.reply('❌ Geçersiz komut! Sadece `egitimduyuru` veya `bransalim` kullanabilirsiniz.')
        return
    
    silinecek_keyler = [key for key in cooldowns.keys() if key.endswith(f'-{komut}')]
    silinen_sayi = len(silinecek_keyler)
    
    for key in silinecek_keyler:
        del cooldowns[key]
    
    if silinen_sayi > 0:
        await ctx.reply(f'✅ `!{komut}` komutu için toplam {silinen_sayi} kullanıcının cooldown\'u kaldırıldı!')
    else:
        await ctx.reply(f'ℹ️ `!{komut}` komutu için aktif cooldown bulunamadı.')

# ═══════════════════════════════════════════════════════════════
# KOMUT - DM GÖNDER
# ═══════════════════════════════════════════════════════════════

# DM gönder durumu
dm_gonder_durumu = {
    'aktif': False, 'duraklatildi': False, 'basarili': 0,
    'basarisiz': 0, 'toplam': 0, 'simdiki': 0
}

@bot.command(name='dmgonder')
async def dm_gonder(ctx, hedef: str = None):
    """
    Belirtilen kişilere DM gönder.
    Kullanım:
      !dmgonder aktif       → Discord'da online/idle/dnd olan herkes
      !dmgonder herkes      → Sunucudaki tüm üyeler (botlar hariç)
      !dmgonder rol @Rol    → Belirli bir role sahip herkes
    Komutu yazdıktan sonra mesajınızı yazın, bot DM olarak iletecek.
    """
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanma yetkiniz yok!')
        return

    if dm_gonder_durumu['aktif']:
        await ctx.reply('⚠️ Zaten aktif bir DM gönderimi var! Bitmesini bekleyin.')
        return

    if not hedef:
        await ctx.reply(
            '❌ Kullanım:\n'
            '`!dmgonder aktif` → Online/idle/dnd olan herkes\n'
            '`!dmgonder herkes` → Tüm üyeler\n'
            '`!dmgonder rol @RolAdı` → Belirli role sahip herkes'
        )
        return

    # Hedef belirleme
    hedef_listesi = []

    if hedef.lower() == 'aktif':
        hedef_listesi = [
            m for m in ctx.guild.members
            if not m.bot and m.status in [
                discord.Status.online,
                discord.Status.idle,
                discord.Status.dnd
            ]
        ]
        hedef_tanim = '🟢 Online/Idle/DND olan üyeler'

    elif hedef.lower() == 'herkes':
        hedef_listesi = [m for m in ctx.guild.members if not m.bot]
        hedef_tanim = '👥 Tüm sunucu üyeleri'

    elif hedef.lower() == 'rol':
        # Rol mention kontrolü
        if not ctx.message.role_mentions:
            await ctx.reply('❌ Rol belirtmediniz! Örnek: `!dmgonder rol @Subay`')
            return
        rol = ctx.message.role_mentions[0]
        hedef_listesi = [m for m in rol.members if not m.bot]
        hedef_tanim = f'🎖️ {rol.name} rolündeki üyeler'

    else:
        await ctx.reply(
            '❌ Geçersiz hedef!\n'
            'Kullanım: `aktif`, `herkes` veya `rol @RolAdı`'
        )
        return

    if not hedef_listesi:
        await ctx.reply('⚠️ Belirtilen kriterlere uygun üye bulunamadı!')
        return

    # Mesajı bekle
    bilgi_embed = discord.Embed(
        title='📨 DM GÖNDERİMİ - MESAJ BEKLENİYOR',
        description=(
            f'**Hedef:** {hedef_tanim}\n'
            f'**Kişi Sayısı:** {len(hedef_listesi)}\n\n'
            f'📝 **Göndermek istediğiniz mesajı yazın.**\n'
            f'İptal etmek için `iptal` yazın.'
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    bilgi_embed.set_footer(text=f'Komutu veren: {ctx.author.name}')
    await ctx.reply(embed=bilgi_embed)

    # Mesajı al
    def mesaj_check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        cevap = await bot.wait_for('message', timeout=120.0, check=mesaj_check)
    except asyncio.TimeoutError:
        await ctx.send('⏱️ 2 dakika içinde mesaj yazılmadı, işlem iptal edildi.')
        return

    if cevap.content.lower() == 'iptal':
        await ctx.send('❌ DM gönderimi iptal edildi.')
        return

    mesaj_icerik = cevap.content

    # Onay al
    onay_embed = discord.Embed(
        title='⚠️ ONAY GEREKLİ',
        description=(
            f'**Hedef:** {hedef_tanim}\n'
            f'**Kişi Sayısı:** {len(hedef_listesi)}\n\n'
            f'**Gönderilecek Mesaj:**\n```\n{mesaj_icerik[:900]}\n```\n\n'
            f'✅ Onaylamak için reaksiyona tıklayın.\n'
            f'❌ İptal etmek için reaksiyona tıklayın.'
        ),
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    onay_mesaji = await ctx.send(embed=onay_embed)
    await onay_mesaji.add_reaction('✅')
    await onay_mesaji.add_reaction('❌')

    def reaksiyon_check(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) in ['✅', '❌']
            and reaction.message.id == onay_mesaji.id
        )

    try:
        reaction, _ = await bot.wait_for('reaction_add', timeout=30.0, check=reaksiyon_check)
    except asyncio.TimeoutError:
        await onay_mesaji.edit(embed=discord.Embed(
            title='⏱️ Zaman Aşımı',
            description='İşlem iptal edildi.',
            color=discord.Color.orange()
        ))
        await onay_mesaji.clear_reactions()
        return

    await onay_mesaji.clear_reactions()

    if str(reaction.emoji) == '❌':
        await onay_mesaji.edit(embed=discord.Embed(
            title='❌ İptal Edildi',
            description='DM gönderimi iptal edildi.',
            color=discord.Color.red()
        ))
        return

    # Gönderim başlat
    dm_gonder_durumu['aktif'] = True
    dm_gonder_durumu['duraklatildi'] = False
    dm_gonder_durumu['basarili'] = 0
    dm_gonder_durumu['basarisiz'] = 0
    dm_gonder_durumu['toplam'] = len(hedef_listesi)
    dm_gonder_durumu['simdiki'] = 0

    ilerleme_mesaji = await ctx.send(
        f'📨 DM gönderimi başlatıldı...\n'
        f'👥 Toplam: {len(hedef_listesi)} kişi'
    )

    for index, member in enumerate(hedef_listesi, 1):
        if not dm_gonder_durumu['aktif']:
            try:
                await ilerleme_mesaji.edit(
                    content=(
                        f'❌ DM gönderimi iptal edildi!\n'
                        f'📊 İlerleme: {index - 1}/{len(hedef_listesi)}\n'
                        f'✅ Başarılı: {dm_gonder_durumu["basarili"]} '
                        f'| ❌ Başarısız: {dm_gonder_durumu["basarisiz"]}'
                    )
                )
            except:
                pass
            return

        while dm_gonder_durumu['duraklatildi']:
            await asyncio.sleep(1)
            if not dm_gonder_durumu['aktif']:
                try:
                    await ilerleme_mesaji.edit(
                        content=(
                            f'❌ DM gönderimi iptal edildi!\n'
                            f'📊 İlerleme: {index - 1}/{len(hedef_listesi)}\n'
                            f'✅ Başarılı: {dm_gonder_durumu["basarili"]} '
                            f'| ❌ Başarısız: {dm_gonder_durumu["basarisiz"]}'
                        )
                    )
                except:
                    pass
                return

        dm_gonder_durumu['simdiki'] = index

        try:
            await member.send(mesaj_icerik)
            dm_gonder_durumu['basarili'] += 1
        except Exception as e:
            dm_gonder_durumu['basarisiz'] += 1
            print(f'DM gönderilemedi ({member.name}): {e}')

        if index % 10 == 0 or index == len(hedef_listesi):
            try:
                await ilerleme_mesaji.edit(
                    content=(
                        f'📨 DM gönderimi devam ediyor...\n'
                        f'📊 İlerleme: {index}/{len(hedef_listesi)}\n'
                        f'✅ Başarılı: {dm_gonder_durumu["basarili"]} '
                        f'| ❌ Başarısız: {dm_gonder_durumu["basarisiz"]}'
                    )
                )
            except:
                pass

        await asyncio.sleep(0.5)

    dm_gonder_durumu['aktif'] = False
    dm_gonder_durumu['duraklatildi'] = False

    sonuc_embed = discord.Embed(
        title='✅ DM GÖNDERİMİ TAMAMLANDI',
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    sonuc_embed.add_field(name='👥 Toplam Hedef', value=str(dm_gonder_durumu['toplam']), inline=True)
    sonuc_embed.add_field(name='✅ Başarılı', value=str(dm_gonder_durumu['basarili']), inline=True)
    sonuc_embed.add_field(name='❌ Başarısız', value=str(dm_gonder_durumu['basarisiz']), inline=True)
    sonuc_embed.set_footer(text=f'İşlemi yapan: {ctx.author.name}')
    await ctx.send(embed=sonuc_embed)


@bot.command(name='dmiptal')
async def dm_iptal(ctx):
    """Devam eden DM gönderimini iptal et"""
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanma yetkiniz yok!')
        return

    if not dm_gonder_durumu['aktif']:
        await ctx.reply('ℹ️ Şu anda aktif bir DM gönderimi yok.')
        return

    dm_gonder_durumu['aktif'] = False
    dm_gonder_durumu['duraklatildi'] = False
    await ctx.reply(
        f'❌ DM gönderimi iptal edildi!\n'
        f'📊 {dm_gonder_durumu["simdiki"]}/{dm_gonder_durumu["toplam"]} kişiye ulaşıldı.\n'
        f'✅ Başarılı: {dm_gonder_durumu["basarili"]} | ❌ Başarısız: {dm_gonder_durumu["basarisiz"]}'
    )


@bot.command(name='dmdur')
async def dm_dur(ctx):
    """Devam eden DM gönderimini duraklat"""
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanma yetkiniz yok!')
        return

    if not dm_gonder_durumu['aktif']:
        await ctx.reply('ℹ️ Şu anda aktif bir DM gönderimi yok.')
        return

    if dm_gonder_durumu['duraklatildi']:
        await ctx.reply('⚠️ DM gönderimi zaten duraklatılmış! `!dmdevam` ile devam edebilirsiniz.')
        return

    dm_gonder_durumu['duraklatildi'] = True
    await ctx.reply(
        f'⏸️ DM gönderimi duraklatıldı!\n'
        f'📊 İlerleme: {dm_gonder_durumu["simdiki"]}/{dm_gonder_durumu["toplam"]}\n'
        f'`!dmdevam` yazarak devam edebilirsiniz.'
    )


@bot.command(name='dmdevam')
async def dm_devam(ctx):
    """Duraklatılmış DM gönderimini devam ettir"""
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanma yetkiniz yok!')
        return

    if not dm_gonder_durumu['aktif']:
        await ctx.reply('ℹ️ Şu anda aktif bir DM gönderimi yok.')
        return

    if not dm_gonder_durumu['duraklatildi']:
        await ctx.reply('⚠️ DM gönderimi zaten devam ediyor!')
        return

    dm_gonder_durumu['duraklatildi'] = False
    await ctx.reply('▶️ DM gönderimi devam ediyor!')


# ════════════════════════════════════════════════════════════════
# PART 3 SONU
# ════════════════════════════════════════════════════════════════
"""
════════════════════════════════════════════════════════════════
PART 4/4: SAVAŞ SİSTEMİ, EK KOMUTLAR & BOT BAŞLATMA
════════════════════════════════════════════════════════════════
Bu dosyayı Part 3'ün sonuna ekleyin
════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - SAVAŞ SİSTEMİ
# ═══════════════════════════════════════════════════════════════

@bot.command(name='savas')
async def savas(ctx):
    """Aktif üyelere savaş duyurusu gönder"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    if savas_durumu['aktif']:
        await ctx.reply('⚠️ Zaten aktif bir savaş duyurusu var! `!durum` ile kontrol edebilirsiniz.')
        return

    try:
        await ctx.message.delete()
    except Exception as e:
        print(f'Mesaj silinemedi: {e}')

    savas_durumu['aktif'] = True
    savas_durumu['duraklatildi'] = False
    savas_durumu['basarili'] = 0
    savas_durumu['basarisiz'] = 0
    savas_durumu['simdiki'] = 0
    savas_durumu['kanal'] = ctx.channel

    status_msg = await ctx.send('⚔️ Savaş duyurusu gönderiliyor... Subaylara DM atılıyor!')

    aktif_uyeler = []
    
    for member in ctx.guild.members:
        if member.bot or member.status not in [discord.Status.online, discord.Status.idle, discord.Status.dnd]:
            continue
        
        player_data, _ = oyuncu_bul(member.name)
        
        if player_data:
            roblox_user_id = player_data.get('roblox_id')
            
            if roblox_user_id:
                is_officer, rank, rank_name = await subay_mi_kontrol(roblox_user_id)
                
                if is_officer:
                    aktif_uyeler.append(member)
    
    savas_durumu['toplam'] = len(aktif_uyeler)
    
    if len(aktif_uyeler) == 0:
        await ctx.send('⚠️ Aktif subay bulunamadı!')
        savas_durumu['aktif'] = False
        return

    for index, member in enumerate(aktif_uyeler, 1):
        if not savas_durumu['aktif']:
            await ctx.send('❌ Savaş duyurusu iptal edildi!')
            return

        while savas_durumu['duraklatildi']:
            await asyncio.sleep(1)
            if not savas_durumu['aktif']:
                await ctx.send('❌ Savaş duyurusu iptal edildi!')
                return

        savas_durumu['simdiki'] = index

        try:
            await member.send(Formatlar.savas_dm())
            savas_durumu['basarili'] += 1
        except Exception as e:
            savas_durumu['basarisiz'] += 1
            print(f'DM gönderilemedi ({member.name}): {e}')

        if index % 10 == 0 or index == len(aktif_uyeler):
            try:
                await status_msg.edit(
                    content=f'⚔️ Savaş duyurusu gönderiliyor...\n'
                            f'📊 İlerleme: {index}/{len(aktif_uyeler)}\n'
                            f'📊 Başarılı: {savas_durumu["basarili"]} | Başarısız: {savas_durumu["basarisiz"]}'
                )
            except:
                pass

        await asyncio.sleep(0.5)

    savas_durumu['aktif'] = False
    savas_durumu['duraklatildi'] = False
    
    await ctx.send(
        f'✅ Savaş duyurusu tamamlandı!\n'
        f'👥 Toplam Aktif Üye: {savas_durumu["toplam"]}\n'
        f'📊 Başarılı: {savas_durumu["basarili"]} | Başarısız: {savas_durumu["basarisiz"]}'
    )


@bot.command(name='durum')
async def durum(ctx):
    """Savaş duyurusu durumunu göster"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    if not savas_durumu['aktif']:
        await ctx.send('ℹ️ Şu anda aktif bir savaş duyurusu yok.')
        return

    durum_emoji = '⏸️ DURAKLATILDI' if savas_durumu['duraklatildi'] else '▶️ DEVAM EDİYOR'
    
    await ctx.send(
        f'📊 **SAVAŞ DUYURUSU DURUMU**\n\n'
        f'**Durum:** {durum_emoji}\n'
        f'**İlerleme:** {savas_durumu["simdiki"]}/{savas_durumu["toplam"]}\n'
        f'**Başarılı:** {savas_durumu["basarili"]}\n'
        f'**Başarısız:** {savas_durumu["basarisiz"]}\n'
        f'**Kalan:** {savas_durumu["toplam"] - savas_durumu["simdiki"]}'
    )


@bot.command(name='dur')
async def dur(ctx):
    """Savaş duyurusunu duraklat"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    if not savas_durumu['aktif']:
        await ctx.send('ℹ️ Şu anda aktif bir savaş duyurusu yok.')
        return

    if savas_durumu['duraklatildi']:
        await ctx.send('⚠️ Savaş duyurusu zaten duraklatılmış!')
        return

    savas_durumu['duraklatildi'] = True
    await ctx.send('⏸️ Savaş duyurusu duraklatıldı! `!devam` yazarak devam edebilirsiniz.')


@bot.command(name='devam')
async def devam(ctx):
    """Duraklatılmış savaş duyurusunu devam ettir"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    if not savas_durumu['aktif']:
        await ctx.send('ℹ️ Şu anda aktif bir savaş duyurusu yok.')
        return

    if not savas_durumu['duraklatildi']:
        await ctx.send('⚠️ Savaş duyurusu zaten devam ediyor!')
        return

    savas_durumu['duraklatildi'] = False
    await ctx.send('▶️ Savaş duyurusu devam ediyor!')


@bot.command(name='iptal')
async def iptal(ctx):
    """Savaş duyurusunu tamamen iptal et"""
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    if not savas_durumu['aktif']:
        await ctx.send('ℹ️ Şu anda aktif bir savaş duyurusu yok.')
        return

    savas_durumu['aktif'] = False
    savas_durumu['duraklatildi'] = False
    
    await ctx.send(
        f'❌ Savaş duyurusu iptal edildi!\n'
        f'📊 {savas_durumu["simdiki"]}/{savas_durumu["toplam"]} kişiye ulaşıldı.\n'
        f'✅ Başarılı: {savas_durumu["basarili"]} | ❌ Başarısız: {savas_durumu["basarisiz"]}'
    )

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - DİĞER & EK FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════

@bot.command(name='ping')
async def ping(ctx):
    """Bot'un gecikme süresini göster"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Gecikme: **{latency}ms**",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if latency < 100:
        embed.add_field(name="Durum", value="🟢 Mükemmel", inline=False)
    elif latency < 200:
        embed.add_field(name="Durum", value="🟡 İyi", inline=False)
    else:
        embed.add_field(name="Durum", value="🔴 Yavaş", inline=False)
    
    await ctx.send(embed=embed)


@bot.command(name='aktiflik-sorgula')
async def aktiflik_sorgula(ctx, roblox_username: str):
    """Bir oyuncunun Roblox aktifliğini otomatik olarak sorgula"""
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanmak için yetkiniz yok!')
        return
    
    await ctx.reply(f'🔍 {roblox_username} kullanıcısının aktifliği sorgulanıyor...')
    
    user_id = await roblox_kullanici_id_al(roblox_username)
    
    if not user_id:
        await ctx.reply(f'❌ Roblox kullanıcısı bulunamadı: {roblox_username}')
        return
    
    success_weekly, weekly_data = await roblox_haftalik_aktiflik_al(user_id)
    success_total, total_data = await roblox_toplam_aktiflik_al(user_id)
    
    if not success_weekly or not success_total:
        await ctx.reply(f'❌ Aktiflik verileri alınamadı!')
        return
    
    weekly_hours = weekly_data // 3600
    weekly_minutes = (weekly_data % 3600) // 60
    total_hours = total_data // 3600
    total_minutes = (total_data % 3600) // 60
    renk_emoji = renk_bul(weekly_hours)
    
    embed = discord.Embed(
        title=f"📊 {roblox_username} - Aktiflik Raporu",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name=f"{renk_emoji} Haftalık Aktiflik",
        value=f"**{weekly_hours}** saat **{weekly_minutes}** dakika",
        inline=True
    )
    
    embed.add_field(
        name="📈 Toplam Aktiflik",
        value=f"**{total_hours}** saat **{total_minutes}** dakika",
        inline=True
    )
    
    embed.add_field(name="🔗 Roblox ID", value=f"`{user_id}`", inline=False)
    embed.set_footer(text=f"Sorgu: {ctx.author.name}")
    
    await ctx.reply(embed=embed)


@bot.command(name='haftalik-rapor')
async def haftalik_rapor(ctx):
    """Tüm kayıtlı subayların haftalık aktiflik raporunu oluştur"""
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanmak için yetkiniz yok!')
        return
    
    await ctx.reply('📊 Haftalık aktiflik raporu hazırlanıyor...')
    
    db = veritabani_yukle()
    players = db.get('players', [])
    
    if not players:
        await ctx.reply('❌ Veritabanında kayıtlı oyuncu yok!')
        return
    
    subay_listesi = []
    
    for player in players:
        roblox_id = player.get('roblox_id')
        roblox_username = player.get('roblox_username')
        
        if not roblox_id or not roblox_username:
            continue
        
        is_officer, rank, rank_name = await subay_mi_kontrol(roblox_id)
        
        if is_officer:
            subay_listesi.append({
                'roblox_id': roblox_id,
                'roblox_username': roblox_username,
                'rutbe': rank_name,
                'rank': rank
            })
        
        await asyncio.sleep(0.1)
    
    if not subay_listesi:
        await ctx.reply('❌ Subay bulunamadı!')
        return
    
    user_ids = [s['roblox_id'] for s in subay_listesi]
    aktiflik_verileri = await roblox_toplu_aktiflik_al(user_ids)
    
    yesil_liste = []
    sari_liste = []
    kirmizi_liste = []
    
    for subay in subay_listesi:
        user_id = subay['roblox_id']
        username = subay['roblox_username']
        rutbe = subay['rutbe']
        
        weekly_seconds = aktiflik_verileri.get(user_id, 0)
        weekly_hours = weekly_seconds / 3600
        
        subay_data = {
            'username': username,
            'rutbe': rutbe,
            'hours': weekly_hours,
            'formatted': saniye_saat_donustur(weekly_seconds)
        }
        
        if weekly_hours >= 7:
            yesil_liste.append(subay_data)
        elif weekly_hours >= 5:
            sari_liste.append(subay_data)
        else:
            kirmizi_liste.append(subay_data)
    
    embed = discord.Embed(
        title="📊 HAFTALIK AKTİFLİK RAPORU",
        description=f"Toplam Subay: **{len(subay_listesi)}** (Grup {SUBAY_KONTROL_GRUP_ID}, Rank {SUBAY_MIN_RANK}+)",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if yesil_liste:
        yesil_text = "\n".join([
            f"🟢 **{s['username']}** ({s['rutbe']}) - {s['formatted']}"
            for s in sorted(yesil_liste, key=lambda x: x['hours'], reverse=True)
        ])
        embed.add_field(
            name=f"🟢 Aktif ({len(yesil_liste)} kişi - 7+ saat)",
            value=yesil_text[:1024],
            inline=False
        )
    
    if sari_liste:
        sari_text = "\n".join([
            f"🟡 **{s['username']}** ({s['rutbe']}) - {s['formatted']}"
            for s in sorted(sari_liste, key=lambda x: x['hours'], reverse=True)
        ])
        embed.add_field(
            name=f"🟡 Orta ({len(sari_liste)} kişi - 5-7 saat)",
            value=sari_text[:1024],
            inline=False
        )
    
    if kirmizi_liste:
        kirmizi_text = "\n".join([
            f"🔴 **{s['username']}** ({s['rutbe']}) - {s['formatted']}"
            for s in sorted(kirmizi_liste, key=lambda x: x['hours'], reverse=True)
        ])
        embed.add_field(
            name=f"🔴 İnaktif ({len(kirmizi_liste)} kişi - 5 saatten az)",
            value=kirmizi_text[:1024],
            inline=False
        )
    
    embed.set_footer(text=f"Rapor: {ctx.author.name}")
    await ctx.reply(embed=embed)


@bot.command(name='api-test')
async def api_test(ctx):
    """Roblox API bağlantısını ve DataStore erişimini test et"""
    if not yetki_kontrol(ctx):
        await ctx.reply('❌ Bu komutu kullanmak için yetkiniz yok!')
        return
    
    embed = discord.Embed(
        title="🔧 API Bağlantı Testi",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    
    if not ROBLOX_API_KEY_GROUPS or ROBLOX_API_KEY_GROUPS == "YOUR_GROUP_API_KEY":
        embed.add_field(name="❌ Grup API Key", value="API Key tanımlanmamış!", inline=False)
    else:
        embed.add_field(name="✅ Grup API Key", value="Tanımlı (Artık kullanılmıyor)", inline=False)
    
    if not ROBLOX_API_KEY_DATASTORE or ROBLOX_API_KEY_DATASTORE == "YOUR_DATASTORE_API_KEY":
        embed.add_field(name="❌ DataStore API Key", value="API Key tanımlanmamış!", inline=False)
    else:
        embed.add_field(name="✅ DataStore API Key", value="Tanımlı (Aktiflik için)", inline=False)
    
    if not UNIVERSE_ID or UNIVERSE_ID == "YOUR_UNIVERSE_ID":
        embed.add_field(name="❌ Universe ID", value="Universe ID tanımlanmamış!", inline=False)
    else:
        embed.add_field(name="✅ Universe ID", value=f"`{UNIVERSE_ID}`", inline=False)
    
    # 🆕 COOKIE TESTİ
    if not ROBLOX_COOKIE or ROBLOX_COOKIE == "YOUR_ROBLOSECURITY_COOKIE":
        embed.add_field(name="❌ Roblox Cookie", value="Cookie tanımlanmamış!", inline=False)
    else:
        cookie_len = len(ROBLOX_COOKIE)
        
        # CSRF token test et
        try:
            async with aiohttp.ClientSession() as session:
                csrf_url = "https://auth.roblox.com/v2/logout"
                headers = {"Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}"}
                
                async with session.post(csrf_url, headers=headers) as response:
                    csrf_token = response.headers.get('x-csrf-token')
                    
                    if csrf_token:
                        # Kullanıcı bilgilerini al
                        user_url = "https://users.roblox.com/v1/users/authenticated"
                        async with session.get(user_url, headers=headers) as user_response:
                            if user_response.status == 200:
                                user_data = await user_response.json()
                                username = user_data.get('name', 'Bilinmiyor')
                                embed.add_field(
                                    name="✅ Roblox Cookie",
                                    value=f"Geçerli! (Uzunluk: {cookie_len})\nGiriş yapılan hesap: **{username}**",
                                    inline=False
                                )
                            else:
                                embed.add_field(
                                    name="⚠️ Roblox Cookie",
                                    value=f"CSRF token alındı ama kullanıcı bilgisi alınamadı\nStatus: {user_response.status}",
                                    inline=False
                                )
                    else:
                        embed.add_field(
                            name="❌ Roblox Cookie",
                            value=f"Cookie geçersiz! (Uzunluk: {cookie_len})\nCSRF token alınamadı.\nÇözüm: Yeni cookie alın",
                            inline=False
                        )
        except Exception as e:
            embed.add_field(
                name="❌ Roblox Cookie Test Hatası",
                value=f"Hata: {str(e)}",
                inline=False
            )
    
    embed.add_field(
        name="ℹ️ Subay Kontrolü",
        value=f"Grup: **{SUBAY_KONTROL_GRUP_ID}** | Min Rank: **{SUBAY_MIN_RANK}+**",
        inline=False
    )
    
    if (ROBLOX_API_KEY_DATASTORE != "YOUR_DATASTORE_API_KEY" and UNIVERSE_ID != "YOUR_UNIVERSE_ID"):
        success, data = await roblox_haftalik_aktiflik_al(1)
        
        if success:
            embed.add_field(name="✅ DataStore Erişimi", value="DataStore'a başarıyla erişildi!", inline=False)
        else:
            embed.add_field(name="❌ DataStore Erişimi", value=f"Hata: {data}", inline=False)
    
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# BOT BAŞLATMA
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print('🌐 Flask sunucusu başlatıldı (Port: 8080)')
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        print('❌ HATA: DISCORD_TOKEN environment variable bulunamadı!')
        print('💡 Token\'ı environment variable olarak ekleyin.')
        print('Örnek: export DISCORD_TOKEN="your_token_here"')
        exit(1)
    
    try:
        print('🚀 Bot başlatılıyor...')
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ Bot başlatma hatası: {e}')
        print('💡 Token\'ınızı kontrol edin.')

# ════════════════════════════════════════════════════════════════
# PART 4 SONU - TÜM KOD TAMAMLANDI!
# ════════════════════════════════════════════════════════════════

"""
════════════════════════════════════════════════════════════════
📦 KURULUM TALİMATI:

1. Tüm 4 part dosyasını indirin
2. Bir metin editörü açın (VSCode, Notepad++ vs.)
3. Part 1'i açın ve kopyalayın
4. Part 2'yi açın ve Part 1'in SONUNA ekleyin
5. Part 3'ü açın ve Part 2'nin SONUNA ekleyin
6. Part 4'ü açın ve Part 3'ün SONUNA ekleyin
7. Dosyayı "discord_bot.py" olarak kaydedin

VEYA

Terminal/CMD'de:
cat bot_part1.py bot_part2.py bot_part3.py bot_part4.py > discord_bot.py

════════════════════════════════════════════════════════════════
🔧 GEREKLİ KÜTÜPHANELER:

pip install discord.py aiohttp flask

════════════════════════════════════════════════════════════════
⚙️ YAPILANDIRMA:

1. YETKILI_ROL_IDS - Discord rol ID'lerinizi ekleyin
2. SUBAY_ROL_ID - Subay rol ID
3. BOT_ROL_ID - Bot yönetici rol ID
4. ROBLOX_API_KEY_GROUPS - Grup işlemleri için API key
5. ROBLOX_API_KEY_DATASTORE - Aktiflik için API key
6. UNIVERSE_ID - Oyun Universe ID
7. DISCORD_TOKEN - Environment variable veya dosyaya ekleyin

════════════════════════════════════════════════════════════════
🚀 ÇALIŞTIRMA:

python discord_bot.py

════════════════════════════════════════════════════════════════
"""
