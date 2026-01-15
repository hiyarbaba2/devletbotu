import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread

# Flask uygulaması (UptimeRobot için)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot çalışıyor! ✅", 200

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "online"}, 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Bot intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Rol ID'lerini environment variable'dan al veya varsayılan değer kullan
SUBAY_ROL_ID = os.getenv('SUBAY_ROL_ID', 'SUBAY_ROL_ID')
BOT_ROL_ID = os.getenv('BOT_ROL_ID', 'BOT_ROL_ID')

# Kanal ID'leri
EGITIM_KANAL_ID = '1127312264718995629'
BRANS_KANAL_ID = '1128667321351815218'

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
        
        yeni_mesaj = Formatlar.bransalim(
            data['host'], 
            data['co'], 
            data['brans'], 
            data['saat'], 
            sartlar
        )
        
        kanal = bot.get_channel(int(data['kanal']))
        await kanal.send(yeni_mesaj)
        await message.reply('✅ Branş alım duyurusu gönderildi!')
        
        # Cooldown'u kaydet
        cooldowns[data['cooldownKey']] = datetime.now()
        
        del bekleyen_kullanicilar[message.author.id]
        return


@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} olarak giriş yaptı!')
    print(f'📊 {len(bot.guilds)} sunucuda aktif')
    print(f'👥 {len(bot.users)} kullanıcıya erişim')
    print('=' * 50)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Bekleyen kullanıcı kontrolü
    if message.author.id in bekleyen_kullanicilar:
        await handle_bekleyen_mesaj(message)
        return

    await bot.process_commands(message)


@bot.command(name='duyuru')
async def duyuru(ctx):
    """Belirli bir kanala mesaj gönder"""
    # Rol kontrolü
    if not any(str(role.id) == BOT_ROL_ID for role in ctx.author.roles):
        await ctx.reply('❌ Bu komutu kullanmak için Bot rolüne sahip olmalısınız!')
        return
    
    bekleyen_kullanicilar[ctx.author.id] = {'adim': 'kanal'}
    await ctx.reply('📢 Hangi kanala mesaj göndermek istiyorsunuz? Kanal ID\'sini yazın:')


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
        while savas_durumu['duraklatildi'] and savas_durumu['aktif']:
            await asyncio.sleep(1)
        
        # Tekrar iptal kontrolü (duraklatma sırasında iptal edilebilir)
        if not savas_durumu['aktif']:
            await ctx.send('❌ Savaş duyurusu iptal edildi!')
            return

        savas_durumu['simdiki'] = index

        try:
            await member.send(Formatlar.savas_dm())
            savas_durumu['basarili'] += 1
        except Exception as e:
            savas_durumu['basarisiz'] += 1
            print(f'{member.name} kullanıcısına DM gönderilemedi: {e}')
        
        # 5 saniye bekleme (rate limit önleme)
        await asyncio.sleep(5)
        
        # Her 10 kişide bir veya son kişide ilerleme güncelle
        if index % 10 == 0 or index == savas_durumu['toplam']:
            try:
                await status_msg.edit(
                    content=f'⚔️ Savaş duyurusu gönderiliyor... ({index}/{savas_durumu["toplam"]})\n'
                            f'📊 Başarılı: {savas_durumu["basarili"]} | Başarısız: {savas_durumu["basarisiz"]}'
                )
            except:
                pass

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
    """Savaş duyurusu durumunu gösterir"""
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
    """Savaş duyurusunu duraklatır"""
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
    """Duraklatılmış savaş duyurusunu devam ettirir"""
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
    """Savaş duyurusunu tamamen iptal eder"""
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

    bekleyen_kullanicilar[ctx.author.id] = {
        'adim': 'brans_sartlar',
        'data': {
            'host': host,
            'co': co,
            'brans': brans,
            'saat': saat,
            'kanal': str(ctx.channel.id),
            'cooldownKey': cooldown_key
        }
    }

    try:
        await ctx.message.delete()
    except Exception as e:
        print(f'Mesaj silinemedi: {e}')

    await ctx.reply('📋 Şartlar olacak mı? Varsa şartları yazın, yoksa "hayır" veya "yok" yazın:')


@bot.command(name='ping')
async def ping(ctx):
    """Bot'un gecikme süresini gösterir"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! Gecikme: {latency}ms')


# Bot'u çalıştır
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
        print('Render\'da Environment Variables kısmına DISCORD_TOKEN ekleyin.')
        exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ Bot başlatma hatası: {e}')
