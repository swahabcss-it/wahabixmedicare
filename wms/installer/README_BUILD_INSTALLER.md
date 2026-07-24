# Windows Installer — How To Build It

I couldn't compile an actual `.exe` for you here because this build
environment is Linux-based with no internet access and no Windows —
there's no way to produce a genuine Windows binary from here. What I've
given you instead is a ready-to-compile **Inno Setup script**, which is
the same tool most commercial Windows installers are built with. Turning
it into `WMS_Setup.exe` takes about 2 minutes on your own Windows PC:

## Steps

1. **Install Inno Setup** (free, official, one-time):
   https://jrsoftware.org/isdl.php

2. **Keep the folder structure as-is** — `installer/wms_installer.iss`
   must sit next to the `wms/` project folder (this is already how the
   zip is laid out).

3. **Double-click `wms_installer.iss`** — it opens in the Inno Setup
   Compiler. Press **Ctrl+F9** (or Build → Compile).

4. Your installer appears at `installer/Output/WMS_Setup.exe`.

## What happens when someone runs WMS_Setup.exe

- It asks for the password `W@hab786` before continuing (change this by
  editing `Password=` in `wms_installer.iss` and recompiling).
- It asks Windows for admin rights (needed to install into Program Files).
- It copies the whole app to `C:\Program Files\WahabixMedicare\wms`.
- It creates Desktop + Start Menu shortcuts.
- Running the shortcut launches `START_HERE_WINDOWS.bat`, which sets up
  the virtual environment (first run only) and starts the server.

## Important — what this password does *not* do

This installer password only controls **who can run the installer** on a
given machine — same as any normal commercial software (Photoshop,
Office, etc. all ask a serial/license during install). It does **not**:
- hide, obfuscate, or restrict the source code after install — everything
  stays plain, readable Python/Django files, as it should for software
  you own and run on your own server
- create any remote lock, kill-switch, or "phone-home" mechanism
- affect the app's own login system (that's the Django admin/staff login,
  a completely separate thing — see `REMOVE_BEFORE_PRODUCTION.md` for the
  testing quick-login buttons on that page)
