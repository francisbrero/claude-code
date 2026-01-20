# Remote Claude Code Setup Guide

Control Claude Code sessions from your phone using Tailscale + Mosh + tmux.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR MAC                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  tmux session "claude"                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  Claude Code                                                  │  │   │
│  │  │  > Working on your code...                                    │  │   │
│  │  │  > (keeps running even when you disconnect)                   │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                              │
│                              │ mosh-server (UDP :60000-61000)              │
│                              │ survives network changes                     │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Tailscale VPN     │
                    │   (encrypted P2P)   │
                    │   no cloud routing  │
                    └──────────┬──────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────────────┐
│                              │                                YOUR PHONE    │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Termius (mosh client)                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  You see and control Claude Code here                         │  │   │
│  │  │  > Can switch WiFi ↔ cellular without disconnecting           │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Components

| Component | What it does |
|-----------|--------------|
| **tmux** | Terminal multiplexer. Keeps Claude running in a session that persists even when you disconnect. You can detach, go home, and reattach later. |
| **Tailscale** | Creates an encrypted peer-to-peer VPN between your devices. Your traffic goes directly Mac↔Phone, never through Tailscale's servers. |
| **Mosh** | "Mobile Shell" - replaces SSH for the connection. Uses UDP instead of TCP, so it survives network switches (WiFi→cellular), high latency, and brief disconnections. |
| **Termius** | SSH/Mosh client app on your phone. Connects to your Mac and displays the terminal. |

### Why Mosh instead of SSH?

```
SSH (TCP):
  Phone ──────── WiFi ──────── Mac
         └─ switch to cellular ─┘
                    ❌ Connection dropped, must reconnect
                    ❌ Lose any unsaved terminal state

Mosh (UDP):
  Phone ──────── WiFi ──────── Mac
         └─ switch to cellular ─┘
                    ✓ Seamlessly continues
                    ✓ Just looks like brief lag
```

SSH uses TCP which requires a persistent connection. If your IP changes (switching networks), the connection dies.

Mosh uses UDP with its own protocol that handles roaming. The server remembers your session, and the client can reconnect from any IP.

### Why tmux?

Without tmux:
```
You close Termius → SSH disconnects → Claude Code exits → Work lost
```

With tmux:
```
You close Termius → Mosh disconnects → tmux keeps running → Claude keeps working
You reconnect → tmux attach → Pick up where you left off
```

---

## Prerequisites

- [x] Mac with Claude Code installed
- [x] Tailscale installed on Mac and iPhone
- [x] Terminus installed on iPhone

---

## Step 1: Connect both devices to Tailscale

**On your Mac:**
```bash
# Start Tailscale (if not already running)
sudo tailscale up
```

**On your iPhone:**
- Open Tailscale app
- Sign in with the same account as your Mac
- Toggle the VPN on

**Verify:** In the Tailscale app on either device, you should see both devices listed. Note your Mac's Tailscale name (e.g., `franciss-macbook-pro`).

---

## Step 2: Enable SSH on your Mac

1. Open **System Settings**
2. Go to **General** → **Sharing**
3. Turn on **Remote Login**
4. Note the username shown (e.g., `ssh francis@franciss-macbook-pro.local`)

---

## Step 3: Install Mosh on your Mac

```bash
brew install mosh
```

Mosh keeps your connection alive when switching networks (WiFi ↔ cellular).

---

## Step 4: Set up SSH key authentication

**On your Mac, generate a key (if you don't have one):**
```bash
# Check if you already have a key
ls ~/.ssh/id_ed25519.pub

# If not, generate one
ssh-keygen -t ed25519
```

**On your iPhone (Terminus):**
1. Open Terminus
2. Go to **Settings** → **Keys**
3. Tap **+** to generate a new key
4. Choose **Ed25519**
5. Copy the public key (tap the key, then copy)

**Add iPhone's public key to your Mac:**
```bash
# Open authorized_keys in an editor
nano ~/.ssh/authorized_keys

# Paste the public key from Terminus on a new line
# Save: Ctrl+O, Enter, Ctrl+X
```

Or use this one-liner if you have the key copied:
```bash
echo "PASTE_YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
```

---

## Step 5: Test SSH connection from Terminus

**In Terminus on your iPhone:**
1. Tap **+** to add a new host
2. Configure:
   - **Alias:** Mac (or whatever you want)
   - **Hostname:** Your Mac's Tailscale name (e.g., `franciss-macbook-pro`)
   - **Username:** Your Mac username (e.g., `francis`)
   - **Keys:** Select the key you created
3. Tap **Connect**

You should see your Mac's terminal prompt.

---

## Step 6: Test Mosh connection

**In Terminus:**
1. Edit your host configuration
2. Enable **Mosh** (there should be a toggle)
3. Connect again

Or connect manually:
```bash
mosh francis@franciss-macbook-pro
```

---

## Step 7: Install the shell helper functions

**On your Mac:**
```bash
# Clone or download the scripts (adjust path as needed)
cd ~/Documents/MadKudu/claude-code

# Add to your .zshrc
echo 'source ~/Documents/MadKudu/claude-code/scripts/claude-remote.zsh' >> ~/.zshrc
echo 'source ~/Documents/MadKudu/claude-code/scripts/claude-headless.zsh' >> ~/.zshrc

# Reload
source ~/.zshrc
```

---

## Step 8: Start a Claude session

**On your Mac:**
```bash
# Navigate to your project
cd ~/Documents/MadKudu/phoenix

# Start Claude in a background tmux session
ccbg

# Or start and attach immediately
cc
```

If you used `cc`, detach with: **Ctrl+B**, then **D**

---

## Step 9: Connect from your phone

**In Terminus:**
1. Connect to your Mac (via Mosh)
2. Attach to the Claude session:
   ```bash
   cca
   ```

You're now controlling Claude Code from your phone!

---

## Quick Reference

| Command | What it does |
|---------|--------------|
| `cc` | Start/attach to project Claude session |
| `ccbg` | Start project session in background |
| `cca` | Quick attach to any Claude session |
| `claude-ls` | List all Claude sessions |
| `claude-send "prompt"` | Send prompt without attaching |
| `Ctrl+B, D` | Detach from tmux (keeps Claude running) |

---

## Troubleshooting

**Can't connect via Tailscale:**
- Make sure both devices show as "Connected" in the Tailscale app
- Try using the Tailscale IP instead of the name (find it in the app)

**SSH works but Mosh doesn't:**
- Ensure Mosh is installed: `brew install mosh`
- Check firewall isn't blocking UDP ports 60000-61000

**"Permission denied" on SSH:**
- Verify the public key is in `~/.ssh/authorized_keys`
- Check file permissions: `chmod 600 ~/.ssh/authorized_keys`

**tmux session not found:**
- Start one first: `ccbg` on your Mac
- List sessions: `tmux ls`
