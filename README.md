# Livekit1 Installation & Usage Guide

This guide will help you set up and run the `livekit1` project on a **new VM** (Ubuntu or Windows), starting from a fresh `git clone`. It covers all dependencies and automations (like `automate.py`).

---

## 1. Prerequisites

- **Git** installed (to clone the repo)
- **Python 3.8+** installed (recommended: Python 3.10+)
- **pip** (Python package manager)
- (Optional) **Docker** and **docker-compose** if you plan to use the `docker-compose.yaml`

---

## 2. Clone the Repository

Open a terminal (Ubuntu) or PowerShell (Windows) and run:

```sh
git clone <your-repo-url>
cd livekit1/livekit
```
Replace `<your-repo-url>` with your actual repository URL.

---

## 3. Set Up Python Environment

**Ubuntu:**
```sh
sudo apt update
sudo apt install python3 python3-pip -y
# (Optional but recommended)
sudo apt install python3-venv -y
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
# If Python is not installed, download and install from python.org
python -m venv venv
.\venv\Scripts\activate
```

---

## 4. Install Python Dependencies

From inside the `livekit` directory:

```sh
pip install -r requirements.txt
```

---

## 5. Configure Your Environment

- **Edit `config.yaml`** and other `.json` files (`dispatch-rule.json`, `inbound-trunk.json`, `outbound-trunk.json`) as needed for your environment (API keys, endpoints, etc.).
- **Edit `key.py`** if it contains sensitive keys or tokens (never commit secrets to git).

---

## 6. (Optional) Set Up Docker (if using docker-compose)

**Ubuntu:**
```sh
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker
```

**Windows:**
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/).

To start services with Docker Compose:
```sh
docker-compose up -d
```

---

## 7. Run the Automation Script

To run your main automation (`automate.py`):

**Ubuntu:**
```sh
python3 automate.py
```

**Windows:**
```powershell
python automate.py
```

---

## 8. Running Other Scripts

- To run the server:  
  **Ubuntu:** `python3 server.py`  
  **Windows:** `python server.py`

- To run the webhook listener:  
  **Ubuntu:** `python3 webhook_listener.py`  
  **Windows:** `python webhook_listener.py`

- To run tests:  
  **Ubuntu:** `python3 test_agent_multiroom.py`  
  **Windows:** `python test_agent_multiroom.py`

---

## 9. (Optional) Set Up as a Service (Ubuntu)

If you want `automate.py` to run on boot, create a systemd service:

```sh
sudo nano /etc/systemd/system/livekit_automate.service
```
Paste:
```
[Unit]
Description=Livekit Automate
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/livekit1/livekit
ExecStart=/path/to/livekit1/livekit/venv/bin/python automate.py
Restart=always

[Install]
WantedBy=multi-user.target
```
Then:
```sh
sudo systemctl daemon-reload
sudo systemctl enable livekit_automate
sudo systemctl start livekit_automate
```
Replace `/path/to/livekit1/livekit` with your actual path.

---

## 10. Troubleshooting

- If you get `ModuleNotFoundError`, ensure your virtual environment is activated and dependencies are installed.
- For permission errors, use `sudo` (Ubuntu) or run as Administrator (Windows).
- Check logs/output for missing environment variables or misconfigured files.

---

## 11. Security & Best Practices

- Never commit secrets or API keys to git.
- Use `.env` files or environment variables for sensitive data.
- Regularly update dependencies for security.

---

### Summary Table

| Step                | Ubuntu Command(s)                                   | Windows Command(s)                |
|---------------------|-----------------------------------------------------|-----------------------------------|
| Clone repo          | `git clone ...`<br>`cd livekit1/livekit`            | Same                              |
| Python venv         | `python3 -m venv venv`<br>`source venv/bin/activate`| `python -m venv venv`<br>`.\\venv\\Scripts\\activate` |
| Install deps        | `pip install -r requirements.txt`                   | Same                              |
| Run automate.py     | `python3 automate.py`                               | `python automate.py`              |
| Docker (optional)   | `sudo apt install docker.io docker-compose -y`      | Install Docker Desktop            |
| Docker Compose      | `docker-compose up -d`                              | Same                              |

---

If you need a sample `config.yaml` or further details on any step, let us know! 