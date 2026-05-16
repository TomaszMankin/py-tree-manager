# Setup

Operational configuration beyond the basic install/run steps. For install + run + test, see [README.md](README.md).

## Email notification setup

The app sends diagnostic email reports to a single recipient when:

- An uncaught exception escapes a UI handler (ERROR severity, auto-sent)
- A CRITICAL exception terminates the app (auto-sent before exit)
- The user clicks the red "Zgłoś błąd" button at the top of the form (REPORT severity, manual)

Emails travel via Gmail SMTP. If the network is unavailable, payloads are queued under `<root>/logs/pending/` and retried every 30 minutes (and on next app start).

### Prerequisites

- A Gmail account that will be used as the sender. This can be the same as the recipient — the simplest setup is one Gmail account that emails itself.
- **2-Step Verification enabled** on that Gmail account. Required by Google to generate App Passwords.

### Step 1: Enable 2-Step Verification on Gmail

If 2FA is not enabled yet on the sending Gmail account:

1. Visit https://myaccount.google.com/security
2. Find "How you sign in to Google" → "2-Step Verification"
3. If it shows "Off", click and follow the setup. Authenticator app or SMS both work.

Skip if already enabled.

### Step 2: Generate a Gmail App Password

1. Visit https://myaccount.google.com/apppasswords (direct link to the App Passwords generator).
   - If you see "App Passwords aren't available for your account", 2FA is not on — see Step 1.
2. Under "App name", type `py-tree-manager` (the name is just a label so you can revoke it later if needed).
3. Click "Create".
4. Google displays a 16-character password formatted with spaces for readability, e.g. `abcd efgh ijkl mnop`. **Copy without the spaces**: `abcdefghijklmnop`.
5. Click "Done". This password cannot be viewed again later. If lost, generate a new one and update the env var (Step 3).

### Step 3: Set the two environment variables

Open PowerShell (regular user, not admin) and run:

```powershell
setx PYTREEMANAGER_EMAIL_PASSWORD "abcdefghijklmnop"
setx PYTREEMANAGER_EMAIL_RECIPIENT "your.email@gmail.com"
```

- Replace `abcdefghijklmnop` with the 16-character App Password from Step 2 (no spaces).
- Replace `your.email@gmail.com` with the Gmail address you want to receive reports at.

`setx` writes to the persistent user environment. The values survive reboots and log out/in.

**Important**: `setx` does NOT update the current PowerShell session. Close this PowerShell window and open a new one before launching the app.

### Step 4: Verify the env vars are set

In a **new** PowerShell window:

```powershell
echo $env:PYTREEMANAGER_EMAIL_RECIPIENT
```

Should print your recipient address.

To verify the password is set without leaking it to screen:

```powershell
$env:PYTREEMANAGER_EMAIL_PASSWORD.Length
```

Should print `16`. If it prints `0` or errors, the env var did not stick — close PowerShell and repeat Step 3.

### Step 5: Test in the app

1. From the new PowerShell session: `cd <your repo clone>` then `python main.py`.
2. App launches. Top-right of the form should show the red "Zgłoś błąd" button.
3. Click the button. Status bar shows "Raport wysłany" (online) or "Raport w kolejce" (offline).
4. Within a few seconds, a `[py-tree-manager REPORT]` email should arrive with today's `journey.log` and `exceptions.log` attached.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Status bar says "w kolejce" but no email arrives even when online | env vars not set in the launching shell | Close all terminals, open fresh PowerShell, verify Step 4, relaunch |
| Status bar says "wysłany" but no email arrives | Wrong recipient address, OR Gmail filtered it to spam | Check Spam folder; verify `PYTREEMANAGER_EMAIL_RECIPIENT` value |
| App crashes on red-button click | Defect (email_helper should self-recover from all failures) | File an issue; route to architect for fallback |
| `<root>/logs/pending/pending_email_*.json` files accumulate | SMTP send is failing silently | Check `<today>__exceptions.log` for SMTP entries; verify App Password is still valid |
| Email arrives but attachments are missing | Today's `journey.log` or `exceptions.log` not yet created | Click around the app first to generate log entries, then click the red button |

### Disabling email (testing without sending)

To temporarily disable email send without losing the local log files:

```powershell
setx PYTREEMANAGER_EMAIL_PASSWORD ""
```

(Set to empty string.) The email_helper reads `os.environ.get(..., "").strip()`, treats empty as unset, and degrades gracefully — local logs still write, the red button still gives "w kolejce" feedback, queue files accumulate (and will retry whenever a valid password reappears).

### Deploying to your father's machine

The same procedure applies. Generate the App Password on YOUR Google account (he does not need his own Gmail), then `setx` both variables on his machine — the password env var with the 16-char App Password, the recipient env var with YOUR Gmail address. He never sees the password.

## Log files

Logs land in `<root>/.PyTreeManager/logs/` where `<root>` is the folder you select when first running the app:

- `<root>/.PyTreeManager/logs/<date>__journey.log` — every UI click. One line per action.
- `<root>/.PyTreeManager/logs/<date>__exceptions.log` — ERROR, CRITICAL, and INFO-CLEANUP entries.
- `<root>/.PyTreeManager/logs/pending/pending_email_<uuid>.json` — queued emails awaiting send.

Files older than 14 days are deleted automatically on app start. No manual cleanup needed.

Logs are `.gitignore`'d — they contain person names and are not committed to the repo.

## Root folder

On first launch the app prompts for a root folder. Point it at a folder that contains (or will contain) a `Lista osób/` directory. The app creates `Drzewo/`, `Rody/`, `Poczekalnia/`, and `.PyTreeManager/` subdirectories under that root automatically.

The root selection is persisted in `%LOCALAPPDATA%\PyTreeManager\last_root.txt`. To change roots, use the menu: Plik → Wybierz osobę-korzeń drzewa.
