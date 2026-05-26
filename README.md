# 🏢 FacTisa Ultra

> سیستم مالی حرفه‌ای برای پیمانکاران و مشاغل کوچک — بر بستر Telegram

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.13-green)](https://aiogram.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)](https://postgresql.org)

## ✨ امکانات

| ماژول | امکانات |
|---|---|
| 📄 **فاکتور** | ساخت، ویرایش، PDF فارسی، مالیات، تخفیف، پرداخت |
| 👥 **مشتری** | ثبت، ویرایش، تاریخچه فاکتور، بدهی |
| 🏗 **پروژه** | بودجه، هزینه، سود/زیان، فاکتور مرتبط |
| 👷 **کارگر** | کارکرد، دستمزد، تسویه، مانده |
| 💰 **مالی** | دریافتی، هزینه، سود/زیان، بدهکاران |
| 📊 **گزارش** | ماهانه، سالانه، خلاصه کارگران |
| 💾 **بکاپ** | خودکار هر ساعت + دستی |

## 🚀 نصب سریع

```bash
# کلون پروژه
git clone https://github.com/moha100h/factisa-ultra.git
cd factisa-ultra

# نصب خودکار
chmod +x install.sh && ./install.sh
```

## ⚙️ نصب دستی

```bash
# کپی .env
cp .env.example .env
nano .env  # مقادیر را وارد کنید

# فونت فارسی (PDF)
mkdir fonts
wget -O fonts/Vazir.ttf https://github.com/rastikerdar/vazir-font/releases/download/v30.1.0/Vazir.ttf
wget -O fonts/Vazir-Bold.ttf https://github.com/rastikerdar/vazir-font/releases/download/v30.1.0/Vazir-Bold.ttf

# راه‌اندازی
docker compose up -d --build
```

## 📊 ساختار پروژه

```
factisa-ultra/
├── app/
│   ├── core/          # config, logger
│   ├── db/            # models (9 table), engine
│   ├── handlers/      # start, clients, invoices, projects, workers, finance, reports
│   ├── keyboards/     # menus with CopyTextButton
│   ├── middlewares/   # db session, auth
│   └── services/      # jalali, pdf, backup, number_gen
├── migrations/        # alembic async
├── fonts/             # Vazir (Persian PDF)
├── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── install.sh
└── .env.example
```

## 📝 دستورات

```bash
docker compose logs -f bot    # لاگ
 docker compose restart bot    # ریستارت
docker compose down           # توقف
```

## 🔒 امنیت

- دسترسی فقط برای ADMIN_IDS
- بکاپ خودکار هر ساعت
- دیتابیس در شبکه داخلی Docker

---

Made with ❤️ by [Mira AI](https://t.me/mira)
