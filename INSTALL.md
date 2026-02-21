# Installation Guide — HE Keyboard as Analog Gamepad

Welcome! This guide will walk you through setting up the Attack Shark X68PRO HE keyboard as a fully analog Xbox 360 controller on Windows. No programming experience required — just follow the steps below.

---

## Prerequisites

Before you begin, make sure you have the following:

- **Windows 10 or 11** (required — there is no Mac or Linux support at this time)
- **Attack Shark X68PRO HE keyboard connected via USB** (Bluetooth will NOT work — the analog data is only available over the wired USB connection)
- **An internet connection** to download the required software

---

## Step 1: Install Python

Python is the programming language that runs this project. You need to install it once.

1. Open your web browser and go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Click the big yellow **"Download Python 3.x.x"** button (any version 3.10 or newer is fine).
3. Run the downloaded installer.
4. **IMPORTANT:** On the very first screen of the installer, check the box that says **"Add Python to PATH"**. This is the most common mistake — if you skip this, later steps will fail.
5. Click **"Install Now"** and wait for it to finish.
6. Click **"Close"** when the installation is complete.

**Alternative (for advanced users):** If you have `winget` available, you can open a terminal and run:
```
winget install Python.Python.3.12
```

**How to verify it worked:** Open Command Prompt (press `Win + R`, type `cmd`, press Enter) and type:
```
python --version
```
You should see something like `Python 3.12.x`. If you see an error instead, uninstall Python and reinstall it, making sure to check "Add Python to PATH."

---

## Step 2: Install the ViGEmBus Driver

ViGEmBus is a special driver that lets your PC create virtual Xbox controllers. Without it, the gamepad emulation will not work.

1. Go to [https://github.com/nefarius/ViGEmBus/releases](https://github.com/nefarius/ViGEmBus/releases)
2. Scroll down to the **Assets** section of the latest release.
3. Download the file ending in `.msi` (for example, `ViGEmBus_Setup_1.22.0_x64_x86_arm64.msi`).
4. Run the downloaded `.msi` file.
5. Click **Next** through each screen of the installer and then click **Install**.
6. If Windows asks for permission (User Account Control), click **Yes**.
7. **A restart may be required.** If the installer asks you to restart, go ahead and do so before continuing.

---

## Step 3: Download This Project

You need to get the project files onto your computer.

### Option A: Download as ZIP (easiest)
1. On the GitHub page for this project, click the green **"Code"** button near the top right.
2. Click **"Download ZIP"**.
3. Once downloaded, right-click the ZIP file and choose **"Extract All..."**
4. Extract it to a location you can easily find, for example: `C:\HE-Gamepad`

### Option B: Use Git (if you have it installed)
Open Command Prompt and run:
```
git clone <repo-url>
```
Replace `<repo-url>` with the actual repository URL.

---

## Step 4: Install Python Dependencies

This project relies on a few extra Python packages (small pieces of software that add functionality). You install them all at once with a single command.

1. Open **Command Prompt**. You can do this by pressing `Win + R`, typing `cmd`, and pressing Enter.
2. Navigate to the project folder by typing the following and pressing Enter:
   ```
   cd C:\HE-Gamepad
   ```
   (Replace `C:\HE-Gamepad` with wherever you extracted the project in Step 3.)
3. Run the following command and press Enter:
   ```
   pip install -r requirements.txt
   ```
4. Wait for it to finish. You will see text scrolling by as it downloads and installs the required packages (things like `vgamepad` for Xbox controller emulation and `pywinusb` for reading keyboard data).
5. When it is done, you should see a message like `Successfully installed ...`.

**If you see "pip is not recognized":** This means Python was not added to PATH. Go back to Step 1 and reinstall Python, making sure to check the "Add Python to PATH" box.

---

## Step 5: First-Time Key Mapping (optional)

A default `key_config.json` file is already included in the project. It is pre-configured for the Attack Shark X68PRO HE keyboard. **If you are using that exact keyboard, you can skip this step entirely.**

You only need to do this if:
- You are using a different HE keyboard model
- Some keys are not being detected correctly
- You want to customize which keys map to which gamepad buttons

If you do need to remap:

1. Open Command Prompt and navigate to the project folder (same as Step 4).
2. Run:
   ```
   python key_mapper_gui.py
   ```
3. A window will appear. It will ask you to press keys on your keyboard one at a time.
4. For each prompt, press the corresponding key (for example, when it says "Press the key for LEFT", press `A`).
5. When finished, the tool will save your mappings to `key_config.json` automatically.

---

## Step 6: Launch the Gamepad

This is the moment of truth — time to turn your keyboard into a controller.

1. Make sure your Attack Shark X68PRO HE is connected via **USB** (not Bluetooth).
2. **Double-click `run.vbs`** in the project folder. The app will start without opening a terminal window.
   - Alternatively, you can open Command Prompt, navigate to the project folder, and run:
     ```
     python virtual_gamepad.py
     ```
3. A window will appear. **Select your mode** from the dropdown at the top:
   - **hybrid** (default) — Only WASD is mapped to the left analog stick. Your keyboard and mouse continue to work normally. Best for games that support simultaneous gamepad + keyboard/mouse (e.g., Halo Infinite, GTA V, Battlefield).
   - **full_controller** — All keyboard keys are mapped to Xbox controller buttons, sticks, and triggers. Best for games that only accept one input type at a time.
4. Click **"ACTIVATE GAMEPAD"**.
5. Your keyboard is now acting as an Xbox 360 controller with full analog input!

**How to verify it is working:**
- Open **Windows Settings** (press `Win + I`).
- Go to **Bluetooth & devices**.
- You should see an **"Xbox 360 Controller"** listed as a connected device.
- You can also search for **"Set up USB game controllers"** in the Start Menu to open the classic game controller test panel.

---

## Step 7: Test in a Game

1. Open any game that supports Xbox/controller input (for example: Forza Horizon, Rocket League, Elden Ring, Celeste, Hollow Knight, etc.).
2. The **left analog stick** is mapped to your WASD keys — but now with analog sensitivity! Pressing a key lightly will tilt the stick gently, and pressing it fully will push the stick all the way.
3. If the movement feels too sensitive or not responsive enough, go back to the gamepad application window and adjust the **deadzone** and **smoothing** sliders until it feels right.

**About modes:**
- In **hybrid** mode, only WASD becomes the analog stick. All other keys still work as keyboard keys and the mouse works normally. This is ideal for shooters and action games where you want analog movement but mouse aiming.
- If the game keeps switching between controller and keyboard prompts (flickering icons), the game does not support simultaneous input. Switch to **full_controller** mode instead.
- You can check if your game supports simultaneous input on the [PCGamingWiki list](https://www.pcgamingwiki.com/wiki/List_of_games_that_support_simultaneous_input).

---

## Troubleshooting

If something goes wrong, check the list below for common issues and fixes.

| Problem | Solution |
|---|---|
| **"ViGEmBus not found"** | Reinstall the ViGEmBus driver (Step 2) and restart your PC. |
| **"Keyboard not detected"** | Make sure the keyboard is connected via **USB**, not Bluetooth. Also close any browser tab that might have a WebHID connection open (the browser web driver can lock the HID interface). |
| **"No analog data"** | Close any other software that might be communicating with the keyboard's HID interface — this includes browser-based keyboard configurators, other keyboard software, or WebHID pages. Only one program can read the HID data at a time. |
| **"pip is not recognized"** | Python was not added to PATH. Uninstall Python and reinstall it, making sure to check **"Add Python to PATH"** on the first screen (Step 1). |
| **"Permission denied"** | Right-click on Command Prompt and choose **"Run as administrator"**, then try the command again. |
| **The virtual controller disappears when the app closes** | This is normal. The virtual Xbox controller only exists while `virtual_gamepad.py` is running. |
| **Game switches between keyboard/controller icons** | The game doesn't support simultaneous gamepad + keyboard/mouse. Switch to **full_controller** mode in the app's mode dropdown. |

---

## Uninstalling

If you want to remove everything:

1. **Delete the project folder** (e.g., `C:\HE-Gamepad`) — this removes all the project files.
2. **Uninstall ViGEmBus** (optional): Open **Windows Settings** > **Apps** > **Installed apps**, find **ViGEmBus**, and click **Uninstall**.
3. **Remove Python packages** (optional): Open Command Prompt and run:
   ```
   pip uninstall vgamepad pywinusb
   ```
   Type `y` and press Enter when asked to confirm each one.
4. **Uninstall Python itself** (optional): Open **Windows Settings** > **Apps** > **Installed apps**, find **Python**, and click **Uninstall**.

---

## Questions or Issues?

If you run into a problem not listed above, feel free to open an issue on the GitHub repository. Include as much detail as you can: what step you were on, what error message you saw, and what keyboard model you are using.

Happy gaming!
