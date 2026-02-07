"""
════════════════════════════════════════════════════════════════
ROBLOX AKTİFLİK TAKİP & YÖNETİM + DUYURU DISCORD BOTU
PART 1/4: YAPILANDIRMA, VERİTABANI & YARDIMCI FONKSİYONLAR
════════════════════════════════════════════════════════════════
Bu dosya:
    - Kütüphaneler ve import'lar
    - Bot yapılandırması
    - Veritabanı yönetimi
    - Yardımcı fonksiyonlar
    - Roblox API fonksiyonları
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
    1234567890,  # Örnek: Kurmay Rolü ID
    9876543210,  # Örnek: Yönetici Rolü ID
]

# Duyuru Bot Rolleri
SUBAY_ROL_ID = os.getenv('SUBAY_ROL_ID', 'SUBAY_ROL_ID')
BOT_ROL_ID = os.getenv('BOT_ROL_ID', 'BOT_ROL_ID')

# Duyuru Kanal ID'leri
EGITIM_KANAL_ID = '1127312264718995629'
BRANS_KANAL_ID = '1128667321351815218'

# Roblox API Ayarları
ROBLOX_API_KEY = "YOUR_ROBLOX_OPEN_CLOUD_API_KEY"
ROBLOX_GRUP_LISTESI = [
    12345678,  # Ana grup ID
    87654321,  # İkinci grup ID
]

# Rütbe Listesi
RUTBE_LISTESI = {
    "Er": 1,
    "Onbaşı": 2,
    "Çavuş": 3,
    "Üsteğmen": 20,
    "Yüzbaşı": 25,
    "Binbaşı": 30,
    "Yarbay": 35,
    "Albay": 40,
    "Tuğgeneral": 50,
    "Tümgeneral": 60,
    "Korgeneral": 70,
    "Orgeneral": 80,
    "Mareşal": 255
}

# Subay Rütbeleri (aktiflik takibi için)
SUBAY_RUTBELERI = [
    "Teğmen", "Üsteğmen", "Yüzbaşı", "Binbaşı",
    "Yarbay", "Albay", "Tuğgeneral", "Tümgeneral",
    "Korgeneral", "Orgeneral", "Mareşal"
]

# Log Kanalı
LOG_CHANNEL_ID = None  # Örnek: 1234567890

# ═══════════════════════════════════════════════════════════════
# GLOBAL DEĞİŞKENLER (Duyuru sistemi için)
# ═══════════════════════════════════════════════════════════════

# Aktif mesaj bekleme durumları
bekleyen_kullanicilar = {}

# Cooldown sistemi
cooldowns = {}

# Savaş duyurusu kontrol sistemi
savas_durumu = {
    'aktif': False,
    'duraklatildi': False,
    'basarili': 0,
    'basarisiz': 0,
    'toplam': 0,
    'simdiki': 0,
    'kanal': None
}

# ═══════════════════════════════════════════════════════════════
# VERİTABANI YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

DATABASE_FILE = 'aktiflik_veritabani.json'
KARALISTE_FILE = 'karaliste.json'

def veritabani_yukle():
    """Aktiflik veritabanını yükle"""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "players": [],
        "settings": {
            "minimum_hours": 5,
            "week_start_day": "monday"
        }
    }

def veritabani_kaydet(data):
    """Aktiflik veritabanını kaydet"""
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def karaliste_yukle():
    """Karaliste veritabanını yükle"""
    if os.path.exists(KARALISTE_FILE):
        with open(KARALISTE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"blacklisted_users": []}

def karaliste_kaydet(data):
    """Karaliste veritabanını kaydet"""
    with open(KARALISTE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def oyuncu_bul(roblox_username):
    """Oyuncuyu veritabanında bul"""
    db = veritabani_yukle()
    for i, player in enumerate(db['players']):
        if player['roblox_username'].lower() == roblox_username.lower():
            return player, i
    return None, None

# ═══════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════

def yetki_kontrol(ctx):
    """Kullanıcının yetki kontrolü"""
    kullanici_rol_ids = [role.id for role in ctx.author.roles]
    return any(rol_id in YETKILI_ROL_IDS for rol_id in kullanici_rol_ids)

def saniye_saat_donustur(saniye):
    """Saniyeyi saat ve dakikaya çevir"""
    saat = saniye // 3600
    dakika = (saniye % 3600) // 60
    return f"{saat}s {dakika}d"

def renk_bul(toplam_saat):
    """Aktiflik saatine göre renk emoji döndür"""
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
    """Roblox kullanıcı adından ID al"""
    url = "https://users.roblox.com/v1/usernames/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"usernames": [username]}) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]['id']
    return None

async def roblox_rutbe_degistir(user_id, rank_id, group_id):
    """Roblox'ta kullanıcının rütbesini değiştir"""
    url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships/{user_id}"
    headers = {
        "x-api-key": ROBLOX_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"role": rank_id}
    
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=payload) as response:
            if response.status == 200:
                return True, "Başarılı"
            else:
                error_text = await response.text()
                return False, f"Hata: {error_text}"

async def roblox_mevcut_rutbe_al(user_id):
    """Kullanıcının mevcut rütbesini al"""
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
    """Kullanıcıyı Roblox grubundan çıkar"""
    url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships/{user_id}"
    headers = {"x-api-key": ROBLOX_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as response:
            return response.status == 200

# ═══════════════════════════════════════════════════════════════
# DUYURU MESAJ FORMATLARI
# ═══════════════════════════════════════════════════════════════

class Formatlar:
    @staticmethod
    def egitimduyuru(host, co, saat):
        """Eğitim duyurusu formatı"""
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
        """Branş alım duyurusu formatı"""
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
        """Savaş DM mesaj formatı"""
        return """@everyone
# Savaş başlıyor Oyuna giriş yap! / Battle is starting now join up!
https://discord.com/channels/1127292848044245133/1200486502870814810
https://www.roblox.com/games/11734871771/YEN-Osmanl-Asker-Oyunu"""

# ═══════════════════════════════════════════════════════════════
# BEKLEME MESAJI YÖNETİCİSİ
# ═══════════════════════════════════════════════════════════════

async def handle_bekleyen_mesaj(message):
    """Bekleyen kullanıcıların mesajlarını işle"""
    user_data = bekleyen_kullanicilar.get(message.author.id)
    if not user_data:
        return

    adim = user_data['adim']

    # !duyuru komutu için kanal seçimi
    if adim == 'kanal':
        kanal_id = message.content.strip()
        try:
            kanal = await bot.fetch_channel(int(kanal_id))
            bekleyen_kullanicilar[message.author.id] = {
                'adim': 'mesaj',
                'kanal': kanal
            }
            await message.reply(f'✅ Kanal seçildi: {kanal.mention}\n📝 Şimdi göndermek istediğiniz mesajı yazın:')
        except Exception as e:
            await message.reply('❌ Geçersiz kanal ID! Lütfen tekrar deneyin:')
            print(f"Kanal fetch hatası: {e}")
        return

    # !duyuru komutu için mesaj gönderme
    if adim == 'mesaj':
        kanal = user_data['kanal']
        try:
            await kanal.send(message.content)
            await message.reply(f'✅ Mesaj başarıyla {kanal.mention} kanalına gönderildi!')
        except Exception as e:
            await message.reply(f'❌ Mesaj gönderilemedi: {str(e)}')
        del bekleyen_kullanicilar[message.author.id]
        return

    # !bransalim komutu için şartlar
    if adim == 'brans_sartlar':
        data = user_data['data']
        sartlar = None if message.content.lower() in ['hayır', 'yok', 'hayir'] else message.content
        
        kanal = bot.get_channel(int(data['kanal']))
        
        # Önce tüm mesajları sil
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
        
        # Duyuruyu oluştur ve gönder
        yeni_mesaj = Formatlar.bransalim(
            data['host'], 
            data['co'], 
            data['brans'], 
            data['saat'], 
            sartlar
        )
        
        await kanal.send(yeni_mesaj)
        
        # Cooldown'u kaydet
        cooldowns[data['cooldownKey']] = datetime.now()
        
        del bekleyen_kullanicilar[message.author.id]
        return

# ═══════════════════════════════════════════════════════════════
# BOT EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    """Bot hazır olduğunda"""
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
    print('AKTIF KOMUTLAR:')
    print('  📊 AKTİFLİK: !komutlar, !logs, !inaktiflikizin, !izinkaldır')
    print('  ⭐ RÜTBE: !tasfiye, !rutbeler')
    print('  🚫 KARALİSTE: !karaliste, !karalistesorgula')
    print('  📢 DUYURU: !egitimduyuru, !bransalim, !duyuru')
    print('  ⚔️ SAVAŞ: !savas, !durum, !dur, !devam, !iptal')
    print('  🔧 DİĞER: !cooldownkaldir, !ping')
    print('═' * 80)

@bot.event
async def on_message(message):
    """Her mesajda çalışır"""
    if message.author.bot:
        return

    # Bekleyen kullanıcı kontrolü
    if message.author.id in bekleyen_kullanicilar:
        await handle_bekleyen_mesaj(message)
        return

    await bot.process_commands(message)

# ════════════════════════════════════════════════════════════════
# PART 1 SONU - PART 2'ye devam edecek...
# ════════════════════════════════════════════════════════════════
"""
════════════════════════════════════════════════════════════════
ROBLOX AKTİFLİK TAKİP & YÖNETİM + DUYURU DISCORD BOTU
PART 2/4: AKTİFLİK TAKİP KOMUTLARI
════════════════════════════════════════════════════════════════
Bu dosya:
    - !komutlar - Komut listesi
    - !logs - Aktiflik sorgulama
    - !inaktiflikizin - İzin verme
    - !izinkaldır - İzni kaldırma
════════════════════════════════════════════════════════════════
"""

# NOT: Bu dosya Part 1'in devamıdır. 
# Çalıştırmak için tüm partları birleştirmeniz gerekir.

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
            "**`!logs <roblox_isim>`** - Belirli oyuncunun detaylı raporu"
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
        name="📢 Duyuru Komutları (Subay Rolü)",
        value=(
            "**`!egitimduyuru <host> <co/yok> <saat>`** - Eğitim duyurusu\n"
            "**`!bransalim <host> <co/yok> <branş> <saat>`** - Branş alım\n"
            "**`!duyuru`** - Özel kanal mesajı"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Savaş Sistemi (Bot Rolü)",
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
        name="🔧 Diğer Komutlar",
        value=(
            "**`!cooldownkaldir <komut>`** - Cooldown kaldır (Bot Rolü)\n"
            "**`!ping`** - Bot gecikmesini göster"
        ),
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
    
    # ALL - Tüm subayları listele
    if hedef.lower() == 'all':
        subaylar = [p for p in db['players'] if p.get('rank') in SUBAY_RUTBELERI]
        
        if not subaylar:
            await ctx.send("❌ Kayıtlı subay bulunamadı!")
            return
        
        # Saatlere göre sırala (en düşükten en yükseğe)
        subaylar.sort(key=lambda x: x.get('weekly_data', {}).get('total_seconds', 0))
        
        embed = discord.Embed(
            title="📊 HAFTALIK AKTİFLİK RAPORU",
            description=f"Toplam {len(subaylar)} subay",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        rapor_metni = ""
        for player in subaylar:
            toplam_saniye = player.get('weekly_data', {}).get('total_seconds', 0)
            toplam_saat = toplam_saniye / 3600
            izinli = player.get('weekly_data', {}).get('on_leave', False)
            
            renk_emoji = renk_bul(toplam_saat)
            izin_emoji = " 🏖️" if izinli else ""
            
            rapor_metni += (
                f"{renk_emoji} **{player['roblox_username']}** - "
                f"{saniye_saat_donustur(toplam_saniye)}{izin_emoji}\n"
            )
        
        # Mesaj 1024 karakterden uzunsa böl
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
            value="🟢 Yeterli (7+ saat) | 🟡 Sınırda (5-7 saat) | 🔴 Yetersiz (<5 saat)",
            inline=False
        )
        
        embed.set_footer(text=f"Sorguyu yapan: {ctx.author.name}")
        
        await ctx.send(embed=embed)
        return
    
    # TEK OYUNCU - Detaylı rapor
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
    
    # Son oturumları göster
    oturumlar = player.get('weekly_data', {}).get('sessions', [])
    if oturumlar:
        son_oturumlar = oturumlar[-5:]  # Son 5 oturum
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
    
    # Zaten izinli mi?
    if player.get('weekly_data', {}).get('on_leave', False):
        await ctx.send(f"⚠️ **{roblox_username}** zaten izinli durumda!")
        return
    
    # İzin ver
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
    
    # İzinli değilse
    if not player.get('weekly_data', {}).get('on_leave', False):
        await ctx.send(f"⚠️ **{roblox_username}** zaten izinli değil!")
        return
    
    # İzni kaldır
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
# PART 2 SONU - PART 3'e devam edecek...
# ════════════════════════════════════════════════════════════════
"""
════════════════════════════════════════════════════════════════
ROBLOX AKTİFLİK TAKİP & YÖNETİM + DUYURU DISCORD BOTU
PART 3/4: RÜTBE, KARALİSTE & DUYURU KOMUTLARI
════════════════════════════════════════════════════════════════
Bu dosya:
    - !tasfiye - Rütbe değiştirme
    - !rutbeler - Rütbe listesi
    - !karaliste - Karalisteye alma
    - !karalistesorgula - Karaliste sorgulama
    - !egitimduyuru - Eğitim duyurusu
    - !bransalim - Branş alım duyurusu
    - !duyuru - Özel kanal mesajı
════════════════════════════════════════════════════════════════
"""

# NOT: Bu dosya Part 1 ve Part 2'nin devamıdır.

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - RÜTBE YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

@bot.command(name='tasfiye')
async def tasfiye(ctx, roblox_username: str = None, *, yeni_rutbe: str = None):
    """Oyuncunun rütbesini değiştir"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not roblox_username or not yeni_rutbe:
        await ctx.send(
            "❌ Kullanım: `!tasfiye <roblox_isim> <yeni_rutbe>`\n"
            "Örnek: `!tasfiye MehmetSubay Er`"
        )
        return
    
    # Rütbe kontrolü
    if yeni_rutbe not in RUTBE_LISTESI:
        await ctx.send(
            f"❌ Geçersiz rütbe! Kullanılabilir rütbeleri görmek için `!rutbeler` yazın."
        )
        return
    
    player, index = oyuncu_bul(roblox_username)
    
    if not player:
        await ctx.send(f"❌ `{roblox_username}` adlı oyuncu bulunamadı!")
        return
    
    # Roblox User ID al
    roblox_user_id = await roblox_kullanici_id_al(roblox_username)
    
    if not roblox_user_id:
        await ctx.send(f"❌ `{roblox_username}` için Roblox ID bulunamadı!")
        return
    
    # Mevcut rütbeyi al
    eski_rutbe = await roblox_mevcut_rutbe_al(roblox_user_id)
    
    # İşlem mesajı
    islem_mesaji = await ctx.send(f"⏳ `{roblox_username}` için tasfiye işlemi başlatıldı...")
    
    # Rütbe değiştir (ilk gruptan dene)
    basarili = False
    mesaj = ""
    
    for group_id in ROBLOX_GRUP_LISTESI:
        rank_id = RUTBE_LISTESI[yeni_rutbe]
        basarili, mesaj = await roblox_rutbe_degistir(roblox_user_id, rank_id, group_id)
        if basarili:
            break
    
    if not basarili:
        await islem_mesaji.edit(content=f"❌ Roblox'ta rütbe değiştirilemedi!\n{mesaj}")
        return
    
    # Veritabanını güncelle
    db = veritabani_yukle()
    db['players'][index]['rank'] = yeni_rutbe
    veritabani_kaydet(db)
    
    embed = discord.Embed(
        title="✅ TASFİYE İŞLEMİ TAMAMLANDI",
        description=f"**{roblox_username}** başarıyla tasfiye edildi.",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="⭐ Rütbe Değişikliği",
        value=f"**Eski Rütbe:** {eski_rutbe}\n**Yeni Rütbe:** {yeni_rutbe}",
        inline=False
    )
    
    embed.set_footer(text=f"İşlemi yapan: {ctx.author.name}")
    
    await islem_mesaji.delete()
    await ctx.send(embed=embed)


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
    """Kullanıcıyı karalisteye al"""
    if not yetki_kontrol(ctx):
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok!")
        return
    
    if not discord_kullanici or not roblox_username or not sebep:
        await ctx.send(
            "❌ Kullanım: `!karaliste @discord_kullanici <roblox_isim> <sebep>`\n"
            "Örnek: `!karaliste @Mehmet#1234 MehmetRBLX Trolling`"
        )
        return
    
    # Onay embed'i
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
    
    # Discord banları
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
    
    # Roblox'tan çıkarma
    roblox_user_id = await roblox_kullanici_id_al(roblox_username)
    
    cikarilan_grup_sayisi = 0
    if roblox_user_id:
        for group_id in ROBLOX_GRUP_LISTESI:
            if await roblox_gruptan_cikar(roblox_user_id, group_id):
                cikarilan_grup_sayisi += 1
    
    # Karaliste veritabanına kaydet
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
    
    # Sonuç embed'i
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
    # Rol kontrolü
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return
    
    bekleyen_kullanicilar[ctx.author.id] = {'adim': 'kanal'}
    await ctx.reply('📢 Hangi kanala mesaj göndermek istiyorsunuz? Kanal ID\'sini yazın:')


@bot.command(name='egitimduyuru')
async def egitimduyuru(ctx, host: str = None, co: str = None, saat: str = None):
    """Eğitim duyurusu gönder"""
    # Rol kontrolü
    if not any(str(role.id) == SUBAY_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için gerekli role sahip değilsiniz!')
        return

    # Kanal kontrolü
    if str(ctx.channel.id) != EGITIM_KANAL_ID:
        await ctx.reply(f'❌ Bu komutu sadece <#{EGITIM_KANAL_ID}> kanalında kullanabilirsiniz!')
        return

    # Cooldown kontrolü
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
    # Rol kontrolü
    if not any(str(role.id) == SUBAY_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için gerekli role sahip değilsiniz!')
        return

    # Kanal kontrolü
    if str(ctx.channel.id) != BRANS_KANAL_ID:
        await ctx.reply(f'❌ Bu komutu sadece <#{BRANS_KANAL_ID}> kanalında kullanabilirsiniz!')
        return

    # Cooldown kontrolü
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

    # Şartlar sorusunu sor
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
    """Tüm kullanıcıların cooldown'unu kaldır (Sadece Bot rolü)"""
    # Rol kontrolü
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return
    
    if not komut:
        await ctx.reply('❌ Kullanım: `!cooldownkaldir egitimduyuru/bransalim`\nÖrnek: `!cooldownkaldir egitimduyuru`')
        return
    
    # Komut kontrolü
    if komut not in ['egitimduyuru', 'bransalim']:
        await ctx.reply('❌ Geçersiz komut! Sadece `egitimduyuru` veya `bransalim` kullanabilirsiniz.')
        return
    
    # İlgili komutu içeren tüm cooldown'ları kaldır
    silinecek_keyler = [key for key in cooldowns.keys() if key.endswith(f'-{komut}')]
    silinen_sayi = len(silinecek_keyler)
    
    for key in silinecek_keyler:
        del cooldowns[key]
    
    if silinen_sayi > 0:
        await ctx.reply(f'✅ `!{komut}` komutu için toplam {silinen_sayi} kullanıcının cooldown\'u kaldırıldı!')
    else:
        await ctx.reply(f'ℹ️ `!{komut}` komutu için aktif cooldown bulunamadı.')

# ════════════════════════════════════════════════════════════════
# PART 3 SONU - PART 4'e devam edecek...
# ════════════════════════════════════════════════════════════════
"""
════════════════════════════════════════════════════════════════
ROBLOX AKTİFLİK TAKİP & YÖNETİM + DUYURU DISCORD BOTU
PART 4/4: SAVAŞ SİSTEMİ & BOT BAŞLATMA
════════════════════════════════════════════════════════════════
Bu dosya:
    - !savas - Savaş duyurusu
    - !durum - Savaş durumu
    - !dur - Savaşı duraklat
    - !devam - Savaşa devam
    - !iptal - Savaşı iptal et
    - !ping - Bot gecikmesi
    - Bot başlatma kodu
════════════════════════════════════════════════════════════════
"""

# NOT: Bu dosya Part 1, 2 ve 3'ün devamıdır.

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - SAVAŞ SİSTEMİ
# ═══════════════════════════════════════════════════════════════

@bot.command(name='savas')
async def savas(ctx):
    """Aktif üyelere savaş duyurusu gönder"""
    # Rol kontrolü
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    # Zaten aktif bir savaş duyurusu varsa
    if savas_durumu['aktif']:
        await ctx.reply('⚠️ Zaten aktif bir savaş duyurusu var! `!durum` ile kontrol edebilirsiniz.')
        return

    try:
        await ctx.message.delete()
    except Exception as e:
        print(f'Mesaj silinemedi: {e}')

    # Durumu sıfırla ve başlat
    savas_durumu['aktif'] = True
    savas_durumu['duraklatildi'] = False
    savas_durumu['basarili'] = 0
    savas_durumu['basarisiz'] = 0
    savas_durumu['simdiki'] = 0
    savas_durumu['kanal'] = ctx.channel

    # İlk bilgilendirme mesajı
    status_msg = await ctx.send('⚔️ Savaş duyurusu gönderiliyor... Aktif üyelere DM atılıyor!')

    # Aktif (online, idle, dnd) üyeleri bul
    aktif_uyeler = [
        member for member in ctx.guild.members 
        if not member.bot and member.status in [discord.Status.online, discord.Status.idle, discord.Status.dnd]
    ]
    savas_durumu['toplam'] = len(aktif_uyeler)

    # Her üyeye mesaj gönder
    for index, member in enumerate(aktif_uyeler, 1):
        # İptal kontrolü
        if not savas_durumu['aktif']:
            await ctx.send('❌ Savaş duyurusu iptal edildi!')
            return

        # Duraklatma kontrolü
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

        # Her 10 kişide bir status güncelle
        if index % 10 == 0 or index == len(aktif_uyeler):
            try:
                await status_msg.edit(
                    content=f'⚔️ Savaş duyurusu gönderiliyor...\n'
                            f'📊 İlerleme: {index}/{len(aktif_uyeler)}\n'
                            f'📊 Başarılı: {savas_durumu["basarili"]} | Başarısız: {savas_durumu["basarisiz"]}'
                )
            except:
                pass

        # Rate limit için kısa bekleme
        await asyncio.sleep(0.5)

    # İşlem tamamlandı
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
    # Rol kontrolü
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
    # Rol kontrolü
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
    # Rol kontrolü
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
    # Rol kontrolü
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return

    if not savas_durumu['aktif']:
        await ctx.send('ℹ️ Şu anda aktif bir savaş duyurusu yok.')
        return

    # İptal et
    savas_durumu['aktif'] = False
    savas_durumu['duraklatildi'] = False
    
    await ctx.send(
        f'❌ Savaş duyurusu iptal edildi!\n'
        f'📊 {savas_durumu["simdiki"]}/{savas_durumu["toplam"]} kişiye ulaşıldı.\n'
        f'✅ Başarılı: {savas_durumu["basarili"]} | ❌ Başarısız: {savas_durumu["basarisiz"]}'
    )

# ═══════════════════════════════════════════════════════════════
# KOMUTLAR - DİĞER
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

# ═══════════════════════════════════════════════════════════════
# BOT BAŞLATMA
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Flask'ı ayrı thread'de başlat (UptimeRobot için)
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print('🌐 Flask sunucusu başlatıldı (Port: 8080)')
    
    # Discord token'ını environment variable'dan al
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        print('❌ HATA: DISCORD_TOKEN environment variable bulunamadı!')
        print('💡 Token\'ı environment variable olarak ekleyin veya direkt yazın.')
        print('Örnek: export DISCORD_TOKEN="your_token_here"')
        
        # Alternatif olarak direkt token yazabilirsiniz (GÜVENLİK RİSKİ!)
        # TOKEN = "BURAYA_BOT_TOKENINIZI_YAZIN"
        exit(1)
    
    try:
        print('🚀 Bot başlatılıyor...')
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ Bot başlatma hatası: {e}')
        print('💡 Token\'ınızı kontrol edin ve bot izinlerini onaylayın.')

# ════════════════════════════════════════════════════════════════
# PART 4 SONU - TÜM PARTLAR TAMAMLANDI!
# ════════════════════════════════════════════════════════════════

"""
════════════════════════════════════════════════════════════════
📚 KULLANIM TALİMATI:

Tüm 4 parçayı birleştirmek için:

1. Tüm part dosyalarını oku
2. Her dosyadaki "@bot.command" decorator'lü fonksiyonları kopyala
3. Part 1'deki yapılandırma ve import'ları al
4. Part 4'teki bot başlatma kodunu kullan

VEYA

Tek bir dosya oluştur ve şu sırayla yapıştır:
- Part 1: Import'lar, yapılandırma, veritabanı, yardımcı fonksiyonlar
- Part 2: Aktiflik komutları
- Part 3: Rütbe, karaliste, duyuru komutları
- Part 4: Savaş sistemi ve bot başlatma

════════════════════════════════════════════════════════════════
🔧 YAPMANIZ GEREKENLER:

Part 1'de:
✅ YETKILI_ROL_IDS - Discord rol ID'lerinizi ekleyin
✅ SUBAY_ROL_ID - Subay rol ID'sini ekleyin
✅ BOT_ROL_ID - Bot yönetici rol ID'sini ekleyin
✅ EGITIM_KANAL_ID - Eğitim kanalı ID'sini kontrol edin
✅ BRANS_KANAL_ID - Branş kanalı ID'sini kontrol edin
✅ ROBLOX_API_KEY - Roblox Open Cloud API key'inizi ekleyin
✅ ROBLOX_GRUP_LISTESI - Grup ID'lerinizi ekleyin
✅ RUTBE_LISTESI - Rütbelerinizi kontrol/düzenleyin

Part 4'te (veya environment variable):
✅ DISCORD_TOKEN - Bot token'ınızı ekleyin

════════════════════════════════════════════════════════════════
📦 GEREKLİ KÜTÜPHANELER:

pip install discord.py aiohttp flask

════════════════════════════════════════════════════════════════
🚀 BOT ÖZELLİKLERİ:

📊 AKTİFLİK TAKİP:
- Roblox oyuncu aktifliklerini takip et
- Haftalık raporlar
- İzin yönetimi

⭐ RÜTBE YÖNETİMİ:
- Otomatik rütbe değiştirme
- Tasfiye sistemi

🚫 KARALİSTE:
- Multi-sunucu ban
- Roblox grup çıkarma
- Karaliste veritabanı

📢 DUYURU SİSTEMİ:
- Eğitim duyuruları
- Branş alım duyuruları
- Cooldown sistemi

⚔️ SAVAŞ SİSTEMİ:
- Toplu DM gönderimi
- Duraklatma/devam sistemi
- İlerleme takibi

🌐 UPTIME:
- Flask health check
- UptimeRobot entegrasyonu

════════════════════════════════════════════════════════════════
"""
