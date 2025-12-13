# 🦅 DittoKiller

> **The Ultimate Clipboard Overlay for Linux, Windows, and macOS.**
> *Always there when you need it, invisible when you don't.*

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-lightgrey)

---

## ✨ Features

- **🚀 Instant Overlay**: Toggle with `<Ctrl>+<Alt>+<Shift>+V` (customizable).
- **📋 History Tracking**: Keeps track of your text and image clipboard history.
- **🖼️ Image Support**: Previews images directly in the list.
- **🔄 Auto-Cleanup**: Automatically removes old items after 7 days.
- **🤖 Native Integration**: Runs as a background service on Linux, Windows, and macOS.
- **⚡ Fast & Lightweight**: Built with PyQt6 for native performance.

---

## 📦 Installation (Linux)

Getting started is easy with our automated installer.

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shadowforce78/DittoKiller.git
   cd DittoKiller
   ```

2. **Run the installer:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

That's it! DittoKiller will start automatically and launch on system boot.

### Manual Service Control

You can manage the application using standard systemd commands:

```bash
# Check status
systemctl --user status dittokiller

# Restart
systemctl --user restart dittokiller

# Stop
systemctl --user stop dittokiller
```

---

## 🛠️ Configuration

Open the overlay (`<Ctrl>+<Alt>+<Shift>+V`) and click the **⚙ Gear Icon** to access settings.

- **Global Hotkey**: Change the shortcut to wake the app.
- **Run on Startup**: Toggle auto-start behavior.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

*Crafted with ❤️ by SaumonDeluxe*
