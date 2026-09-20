# Telegram Inline Voice Bot 🎙

Telegramda inline rejimda tayyor ovozli xabarlarni (`@bot` orqali) lahzada chiqaruvchi, MP3 fayllarni voice formatiga o'tkazuvchi, Telegram kanalini cheksiz fayl ombori (CDN) sifatida ishlatuvchi va to'liq Admin paneliga ega zamonaviy bot.

---

## 🌟 Asosiy Imkoniyatlar

1. **Inline Voice Mode**:
   - Istalgan chatda `@bot_username` deb yozilsa, **hech qanday so'z yozish shart emas** — eng ko'p jo'natilgan mashhur ovozlar ketma-ket chiqib keladi.
   - Agar foydalanuvchi qidirmoqchi bo'lsa, nomini yozib ham qidirishi mumkin.
   - Har safar ovoz yuborilganda uning hisoblagichi (`usage_count`) oshib boradi va mashhurlari doim yuqorida turadi.
2. **Telegram Kanal — Bepul & Cheksiz Xotira**:
   - Barcha audio/voicelar maxsus Telegram kanalda saqlanadi.
   - Bot kanaldagi xabarlarni avtomatik ushlab `file_id` sini Supabase bazasiga kiritadi.
3. **MP3 / Audio -> Voice Konverter**:
   - Botga istalgan `.mp3` yoki audio yuborilsa, tizimdagi `ffmpeg` orqali Telegram Voice (`.ogg` Opus) ga o'tkazib beradi.
   - Qo'shimcha audio effektlar: *Oddiy, Robot, Tezlashtirilgan (Chipmunk), Basoviy (Chuqur)*.
4. **Admin Panel (`/admin`)**:
   - Statistika (foydalanuvchilar, ovozlar, top ovozlar).
   - Yangi ovoz qo'shish (FSM orqali nom berib).
   - Ovozlar ro'yxatini ko'rish va o'chirish.
   - **Ko'p adminlik tizimi**: Superadmin yangi adminlar qo'shishi yoki o'chirishi mumkin.
   - Barcha foydalanuvchilarga xabar tarqatish (Broadcast).
5. **Render.com Bepul Servisiga Moslashgan**:
   - Ichida `Dockerfile` bor (FFmpeg to'liq o'rnatiladi).
   - Kichik HTTP server mavjud bo'lib, Render.com Web Service sifatida uzluksiz ishlaydi.

---

## 🚀 O'rnatish va Sozlash Bosqichlari

### 1-qadam: BotFather sozlamalari
1. [@BotFather](https://t.me/BotFather) ga kiring va `/newbot` orqali yangi bot oching.
2. Bot tokenini saqlab oling.
3. **MUHIM**: BotFather'ga `/setinline` buyrug'ini yuboring, botingizni tanlang va qidiruv matniga masalan: `Ovozlarni qidirish...` deb yozing. Bu orqali **Inline rejim faollashadi**!

### 2-qadam: Telegram Kanal (Storage)
1. Telegramda yangi kanal oching (masalan: `My Voice Storage`).
2. Yangi yaratgan botingizni ushbu kanalga **Admin** qilib qo'shing (xabar yuborish huquqi bilan).
3. Kanal ID sini oling (masalan, `@username_to_id_bot` orqali yoki kanal linkidan, odatda `-100...` bilan boshlanadi).

### 3-qadam: Supabase Sozlash
1. [supabase.com](https://supabase.com) ga kiring va bepul loyiha (Project) oching.
2. Chap menyudan **SQL Editor** bo'limiga o'ting.
3. Loyihadagi `schema.sql` fayli ichidagi barcha SQL kodlarni nusxalab, SQL Editor'ga tashlang va **Run** tugmasini bosing.
4. **Project Settings** -> **API** bo'limidan:
   - `Project URL`
   - `service_role` (yoki `anon public`) API kalitini oling.

---

## ☁️ Render.com ga Bepul Yuklash (Deployment)

1. Ushbu loyihani o'zingizning **GitHub** hisobingizga yangi repozitoriy qilib yuklang (Push qiling).
2. [Render.com](https://render.com) ga kiring va **New +** -> **Web Service** ni tanlang.
3. GitHub repozitoriyingizni ulang.
4. Sozlamalar:
   - **Name**: `inline-voice-bot` (istalgan nom)
   - **Language / Environment**: `Docker` (Dockerfile avtomatik aniqlanadi va FFmpeg o'rnatiladi)
   - **Plan**: `Free`
5. **Environment Variables** (Muhit o'zgaruvchilari) bo'limiga quyidagilarni kiriting:
   - `BOT_TOKEN` = Sizning bot tokeningiz
   - `SUPABASE_URL` = Supabase URL
   - `SUPABASE_KEY` = Supabase API kaliti
   - `STORAGE_CHANNEL_ID` = Telegram kanal ID si (masalan: `-1001234567890`)
   - `ADMIN_GROUP_ID` = Telegram Admin Guruh ID si (Topics ochiladigan guruh, masalan: `-1009876543210`)
   - `SUPERADMIN_ID` = Sizning Telegram raqamli ID ingiz (masalan: `123456789`)
   - `PORT` = `8080`

6. **Create Web Service** tugmasini bosing. Bot bir necha daqiqada ishga tushadi!

> [!TIP]
> **Render.com Bepul Tarifida "uxlab qolmasligi" uchun:**
> Render bepul xizmatlari 15 daqiqa murojaat bo'lmasa uxlab qoladi. Buni oldini olish uchun [UptimeRobot.com](https://uptimerobot.com) yoki [cron-job.org](https://cron-job.org) saytidan bepul ro'yxatdan o'ting va Render bergan URL manzilni (masalan: `https://inline-voice-bot.onrender.com/health`) har 5 daqiqada bir tekshirib turadigan qilib qo'ying. Shunda botingiz 24/7 o'chmasdan ishlaydi!
