# CTE Timeclock

A timeclock application for Career and Technical Education (CTE) classrooms, allowing students to clock in/out using a 6-digit code, with teacher management features.

## Features

### Student Interface (`/`)
- Enter 6-digit code to look up student
- View current clock status (IN/OUT)
- Clock in or out with single button
- Anti-duplicate punch protection
- Responsive design for kiosks, Chromebooks, and phones

### Teacher Interface (`/dashboard/`)
- **Dashboard**: Real-time view of currently clocked-in students
- **Students**: Add, edit, delete students with unique 6-digit codes
- **Punch History**: Search and filter punch records, export to CSV
- **Reports**: Generate weekly time summaries, email reports via Gmail
- **Classes**: Organize students into classes
- **Settings**: Configure Gmail SMTP for email reports
- **Teachers**: Manage teacher accounts
- **Clear Year**: Remove all data for current school year

## Tech Stack

- **Backend**: Python 3.11+ / Django 5.x
- **Database**: MariaDB 10.x
- **Frontend**: Bootstrap 5 / Django Templates
- **Email**: Gmail SMTP with App Passwords

## Installation

### Prerequisites

- Ubuntu 22.04 LTS server
- Python 3.11+
- MariaDB 10.x
- Gmail account with App Password (for email features)

### 1. Clone the Repository

```bash
cd /opt
git clone https://github.com/jlundholm/cteTime.git
cd cteTime
```

### 2. Set Temp Permissions

```bash
sudo chown -R your-username:www-data /opt/cteTime
sudo chmod -R 755 /opt/cteTime
```

### 3. Install System Dependencies

```bash
sudo apt update
sudo apt install python3-venv python3-pip libmysqlclient-dev pkg-config mariadb-server mariadb-client nginx
```

### 4. Create Database

```bash
sudo mysql
```

```sql
CREATE DATABASE cteTime CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cteTime'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON cteTime.* TO 'cteTime'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Configure Environment

```bash
cp .env.example .env
nano .env
```

Update `.env` with your settings:
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-server-ip,your-domain.com

DB_NAME=cteTime
DB_USER=cteTime
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### 7. Run Migrations

```bash
python manage.py migrate
```

### 8. Create Superuser

```bash
python manage.py createsuperuser
```

### 9. Configure Gunicorn

Create systemd service:
```bash
sudo nano /etc/systemd/system/ctetime.service
```

```ini
[Unit]
Description=CTE Timeclock Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/cteTime
ExecStart=/opt/cteTime/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/opt/cteTime/cteTime.sock cteTime.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ctetime
sudo systemctl start ctetime
```

### 10. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/cteTime
```

```nginx
server {
    listen 80;
    server_name your-server-ip-or-domain;

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/cteTime/cteTime.sock;
    }
    
    location /static/ {
        root /opt/cteTime;
    }
}
```

```bash
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/cteTime /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl reload nginx
```

### 11. Set Permissions

```bash
sudo chown -R www-data:www-data /opt/cteTime
sudo chmod -R 755 /opt/cteTime
```

## Gmail Setup for Email Reports

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Navigate to **Security**
3. Enable 2-Step Verification if not already enabled
4. Search for and go to **App passwords**
5. Select "Mail" as the app, "Other" as the device
6. Enter "CTE Timeclock" and click Generate
7. Copy the 16-character password
8. Paste this into the `EMAIL_HOST_PASSWORD` in your `.env` file

## Usage

### Accessing the Application

- **Student Clock**: `http://your-server/`
- **Teacher Login**: `http://your-server/login/`
- **Admin Panel**: `http://your-server/admin/`

### First-Time Setup

1. Log in to the admin panel (`/admin/`)
2. Go to **Email Settings** and configure SMTP
3. Log in to teacher interface (`/login/`)
4. Add students (with unique 6-digit codes)
5. Create classes and assign students
6. Direct students to the clock page

### Weekly Workflow

1. Students clock in/out using their 6-digit code
2. Teachers monitor clocked-in students on dashboard
3. Generate weekly reports at end of week
4. Email reports to yourself via the Reports page
5. Use "Clear Year" at end of school year to reset

## Troubleshooting

### Database Connection Issues
- Verify MariaDB is running: `sudo systemctl status mariadb`
- Check credentials in `.env`
- Test connection: `mysql -u cteTime -p cteTime`

### Email Not Sending
- Verify Gmail App Password is correct
- Ensure 2-Step Verification is enabled on Google account
- Check server logs: `sudo journalctl -u cteTime -f`

### Static Files Not Loading
- Run: `python manage.py collectstatic`
- Check Nginx configuration
- Verify file permissions

## License

MIT License
