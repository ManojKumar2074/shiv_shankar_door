# Shiv Shankar Door — Luxury Door Portfolio Website

A full-stack web application built with Django for a luxury door showroom business. Includes a customer-facing storefront, AI-powered door preview using OpenCV, interactive price estimator, and an owner dashboard for complete product management.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py migrate
```

### 3. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 4. Run the Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` for the website.
Visit `http://127.0.0.1:8000/admin/` for the admin panel.

## Adding Door Designs

Go to admin panel → Doors → Add Door.

Fill in:
- Name, Category, Material, Finish
- Width, Height, Thickness (in mm)
- Price Min and Max (INR)
- Upload main image + up to 3 additional images
- Features (one per line)
- Check "Is Featured" to show on homepage

## Pages

| URL | Page |
|-----|------|
| `/` | Home |
| `/gallery/` | Door Collection (with filters) |
| `/door/<id>/` | Door Detail |
| `/ai-preview/` | AI Door Preview |
| `/about/` | About Us |
| `/contact/` | Contact |
| `/admin/` | Admin Panel |

## Features
- Luxury black/ivory/gold design system
- Playfair Display + Montserrat typography
- Full gallery with category/material/finish/price filters
- AI door preview using OpenCV
- WhatsApp integration (+91 70138 91509)
- Customer inquiry system with admin status tracking
- Mobile responsive layout

## Tech Stack
- Django 4.2 + SQLite
- Pillow (image handling)
- OpenCV (AI preview)
- Pure CSS + JS (no frameworks)
