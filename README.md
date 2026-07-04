# Running Alpine Linux on Android with Chroot-Distro and Magisk

This guide explains how to run an Alpine Linux chroot environment on a rooted Android device using Magisk and Chroot-Distro. It also covers Samba file sharing and automatic startup of a Python bot.

---

# Prerequisites

Before starting, ensure you have:

* An Android device with Magisk root access
* A working ADB installation on your computer
* The Chroot-Distro Magisk module downloaded from GitHub
* Basic familiarity with ADB and Linux commands

---

# Step 1 - Install Chroot-Distro

1. Download the **[chroot-distro.zip](https://github.com/Magisk-Modules-Alt-Repo/chroot-distro/releases)** module from GitHub.
2. Open the Magisk application.
3. Install the module from storage.
4. Reboot the device if required.

---

# Step 2 - Install Alpine Linux

Connect to the device through ADB and obtain root access:

```bash
adb shell
su
```

Verify that Chroot-Distro is installed:

```bash
chroot-distro list
```

Download and install Alpine Linux:

```bash
chroot-distro download alpine
chroot-distro install alpine
```

Exit Alpine if it automatically logs in:

```bash
exit
```

---

# Step 3 - Configure Automatic Alpine Startup

Create a Magisk service script:

```bash
nano /data/adb/service.d/start_alpine.sh
```

Paste the following script:

```bash
#!/system/bin/sh

# Define log path
LOG_FILE="/data/adb/service.d/alpine_boot_log.txt"

# Function to log messages with timestamps
log_msg() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1" >> "$LOG_FILE"
}

echo "
        ----- Script Started -----" >> "$LOG_FILE"

# 60s delay
log_msg "Waiting 60s for system stability..."
sleep 60

# Attempt to mount
log_msg "Attempting to mount Alpine..."
if chroot-distro mount alpine >> "$LOG_FILE" 2>&1; then
    log_msg "SUCCESS: Alpine mounted."
else
    log_msg "ERROR: Alpine mount failed."
fi

# Attempt to login/start background services
log_msg "Attempting to login to Alpine..."
if chroot-distro login alpine >> "$LOG_FILE" 2>&1; then
    log_msg "Alpine is up"
else
    log_msg "ERROR: Alpine login failed."
fi

log_msg "--- Script Finished ---"
```

Make the script executable:

```bash
chmod 755 /data/adb/service.d/start_alpine.sh
```

---

# Step 4 - Install Required Packages

Log back into Alpine:

```bash
chroot-distro login alpine
```

Update repositories:

```bash
apk update
```

Install required packages:

```bash
apk add python3 py3-pip samba
apk add nano
apk add py3-requests
apk add git
```

These packages provide:

| Package  | Purpose                       |
| -------- | ----------------------------- |
| Python 3 | Bot runtime                   |
| pip      | Python package manager        |
| Samba    | SMB file sharing              |
| nano     | Text editor                   |
| requests | HTTP requests for Python bots |

---

# Step 5 - Create a User

Create a user account inside Alpine:

```bash
adduser -D x00td
```

---

# Step 6 - Configure Samba Password

Create a Samba password for the user:

```bash
smbpasswd -a x00td
```

You will be prompted to enter the password twice.

---

# Step 7 - Configure Samba

Remove the default Samba configuration:

```bash
rm -rf /etc/samba/smb.conf
```

Create a directory that will be shared over the network:

```bash
mkdir -p /home/x00td/my_bot
```

Create a new Samba configuration:

```bash
nano /etc/samba/smb.conf
```

Paste the following:

```ini
[global]
   workgroup = WORKGROUP
   server string = X00TD Samba
   security = user
   map to guest = Bad User
   load printers = no

[BotFiles]
   path = /home/x00td/my_bot
   valid users = x00td
   guest ok = no
   writable = yes
   browseable = yes
   force user = root

[InternalStorage]
   path = /mnt/sdcard
   valid users = x00td
   guest ok = no
   writable = yes
   browseable = yes
   force user = root
```

---

# Step 8 - Start Samba Services

Stop any existing Samba instances:

```bash
pkill smbd
pkill nmbd
```

Start fresh instances:

```bash
smbd -D
nmbd -D
```

---

# Step 9 - Create the Bot Directory

Place your bot files inside:

```text
/home/x00td/my_bot
```

Example:

```text
/home/x00td/my_bot/
├── bot.py
├── config.json
└── bot.log
```

---

# Step 10 - Create Bot Configuration

Create a `config.json` file:

```json
{
  "bot_admin_id": "admin chat id",
  "bots": {
    "bot1": "bot token",
    "bot2": "bot token"
  }
}
```

Replace the values with your actual Telegram bot information.

---

# Step 11 - Start the Bot

Run the bot manually:

```bash
python3 /home/x00td/my_bot/bot.py
```

---

# Step 12 - Enable Automatic Startup

Edit Alpine's root profile:

```bash
nano /root/.profile
```

Append the following:

```bash
log_msg(){
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1"
}

# Start Samba if not already running
if ! pgrep -x "smbd" > /dev/null; then
    smbd -D
    nmbd -D
    log msg "Samba services started."
fi

# Start the Python bot if not already running
if ! pgrep -f "bot.py" > /dev/null; then
    nohup python3 /home/x00td/my_bot/bot.py > /home/x00td/my_bot/bot_log.txt 2>&1 &
    log msg "Python bot started in background."
fi
```

This ensures Samba and the bot automatically start whenever Alpine is entered.

---

# Reboot Test

Reboot the device and verify:

* Alpine mounts successfully
* Samba starts automatically
* The bot starts automatically
* SMB shares are accessible from the network

---

# Useful Commands

## View Alpine Boot Logs

```bash
cat /data/adb/service.d/alpine_boot_log.txt
```

## Restart the Bot

```bash
pkill python3
```

Log back into Alpine to trigger the automatic startup logic.

## Push Files Using ADB

```bash
adb push <local_file> /sdcard/
```

Example:

```bash
adb push bot.py /sdcard/
```

---

# Directory Layout

```text
Android Device
│
├── Magisk
│   └── start_alpine.sh
│
├── Alpine Linux
│   ├── Samba
│   ├── Python
│   └── User: x00td
│
└── /home/x00td/my_bot
    ├── bot.py
    ├── config.json
    └── bot.log
```
